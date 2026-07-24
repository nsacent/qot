import hashlib
import hmac

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
import requests as http_requests

from apps.locations.models import City

from .models import User, UserFollow, UserProfile, VerificationCode
from .phone_numbers import normalize_ugandan_phone


class UserProfileSerializer(serializers.ModelSerializer):
    default_city_name = serializers.CharField(
        source="default_city.name",
        read_only=True,
    )
    default_region_name = serializers.CharField(
        source="default_city.region.name",
        read_only=True,
    )

    class Meta:
        model = UserProfile
        fields = [
            "avatar",
            "cover_photo",
            "bio",
            "business_name",
            "default_city",
            "default_city_name",
            "default_region_name",
            "notification_preferences",
            "timezone",
            "trust_score",
            "total_listings",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "trust_score",
            "total_listings",
            "created_at",
            "updated_at",
        ]

    def validate_notification_preferences(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Notification preferences must be an object.")

        allowed_keys = {
            "verification",
            "messages",
            "listing_approvals",
            "listing_rejections",
            "reports",
            "renewals",
            "marketing",
        }
        unknown_keys = set(value) - allowed_keys

        if unknown_keys:
            raise serializers.ValidationError(
                f"Unknown notification preference: {sorted(unknown_keys)[0]}."
            )

        if any(not isinstance(enabled, bool) for enabled in value.values()):
            raise serializers.ValidationError(
                "Every notification preference must be true or false."
            )

        return value

    def validate_timezone(self, value):
        return validate_timezone_name(value)


def validate_timezone_name(value):
    timezone_name = str(value or "").strip()

    if not timezone_name:
        raise serializers.ValidationError("Select a timezone.")

    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as error:
        raise serializers.ValidationError("Select a valid timezone.") from error

    return timezone_name


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    phone_verified = serializers.BooleanField(read_only=True)
    email_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "phone",
            "email",
            "full_name",
            "role",
            "is_verified",
            "phone_verified",
            "phone_verified_at",
            "email_verified",
            "email_verified_at",
            "is_banned",
            "date_joined",
            "profile",
            "followers_count",
            "following_count",
        ]
        read_only_fields = [
            "id",
            "role",
            "is_verified",
            "phone_verified",
            "phone_verified_at",
            "email_verified",
            "email_verified_at",
            "is_banned",
            "date_joined",
            "followers_count",
            "following_count",
        ]

    def get_followers_count(self, obj):
        return obj.follower_relationships.count()

    def get_following_count(self, obj):
        return obj.following_relationships.count()


class RegisterSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(required=True, allow_blank=False)
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            "id",
            "phone",
            "email",
            "full_name",
            "password",
            "password_confirm",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        phone = attrs.get("phone")
        email = attrs.get("email")
        password = attrs.get("password")
        password_confirm = attrs.get("password_confirm")

        if not phone and not email:
            raise serializers.ValidationError(
                "Phone number or email address is required."
            )

        if password != password_confirm:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )

        return attrs

    def validate_phone(self, value):
        try:
            normalized_phone = normalize_ugandan_phone(value)
        except ValueError as error:
            raise serializers.ValidationError(
                str(error)
            ) from error

        if User.objects.filter(phone=normalized_phone).exists():
            raise serializers.ValidationError(
                "An account with this phone number already exists."
            )

        return normalized_phone

    def create(self, validated_data):
        validated_data.pop("password_confirm")

        password = validated_data.pop("password")

        user = User.objects.create_user(
            password=password,
            **validated_data,
        )

        return user


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True)
    keep_signed_in = serializers.BooleanField(
        default=False,
        required=False,
        write_only=True,
    )

    def validate(self, attrs):
        identifier = str(attrs.get("identifier") or "").strip()
        password = attrs.get("password")

        user = None

        if identifier:
            if "@" not in identifier:
                try:
                    phone = normalize_ugandan_phone(identifier)
                except ValueError:
                    phone = identifier

                user = User.objects.filter(phone=phone).first()

            if user is None:
                user = User.objects.filter(email__iexact=identifier).first()

        if user is None:
            raise AuthenticationFailed(
                "The phone/email or password is incorrect."
            )

        if not user.check_password(password):
            raise AuthenticationFailed(
                "The phone/email or password is incorrect."
            )

        if not user.is_active:
            raise PermissionDenied(
                "This account is inactive. Please contact QOT support."
            )

        if user.is_banned:
            raise PermissionDenied(
                "This account has been banned. Please contact QOT support."
            )

        attrs["user"] = user
        return attrs


class GoogleLoginSerializer(serializers.Serializer):
    credential = serializers.CharField(write_only=True)
    keep_signed_in = serializers.BooleanField(
        default=False,
        required=False,
        write_only=True,
    )

    def validate(self, attrs):
        client_id = settings.GOOGLE_OAUTH_CLIENT_ID

        if not client_id:
            raise serializers.ValidationError(
                {"detail": "Google sign-in is not configured on the server."}
            )

        try:
            identity = google_id_token.verify_oauth2_token(
                attrs["credential"],
                google_requests.Request(),
                client_id,
            )
        except (ValueError, TypeError):
            raise serializers.ValidationError(
                {"detail": "Google could not verify this sign-in. Please try again."}
            )

        subject = str(identity.get("sub") or "").strip()
        email = str(identity.get("email") or "").strip().lower()

        if not subject or not email or identity.get("email_verified") is not True:
            raise serializers.ValidationError(
                {"detail": "Google did not provide a verified email address."}
            )

        attrs["identity"] = identity
        return attrs


class FacebookLoginSerializer(serializers.Serializer):
    access_token = serializers.CharField(write_only=True)
    keep_signed_in = serializers.BooleanField(
        default=False,
        required=False,
        write_only=True,
    )

    def _graph_request(self, path, params):
        version = settings.FACEBOOK_GRAPH_API_VERSION

        try:
            response = http_requests.get(
                f"https://graph.facebook.com/{version}/{path}",
                params=params,
                timeout=10,
            )
            payload = response.json()
        except (http_requests.RequestException, ValueError, TypeError) as error:
            raise serializers.ValidationError(
                {"detail": "Facebook could not verify this sign-in. Please try again."}
            ) from error

        if (
            not isinstance(payload, dict)
            or response.status_code >= 400
            or payload.get("error")
        ):
            raise serializers.ValidationError(
                {"detail": "Facebook could not verify this sign-in. Please try again."}
            )

        return payload

    def validate(self, attrs):
        app_id = settings.FACEBOOK_OAUTH_APP_ID
        app_secret = settings.FACEBOOK_OAUTH_APP_SECRET

        if not app_id or not app_secret:
            raise serializers.ValidationError(
                {"detail": "Facebook sign-in is not configured on the server."}
            )

        access_token = attrs["access_token"]
        debug_payload = self._graph_request(
            "debug_token",
            {
                "input_token": access_token,
                "access_token": f"{app_id}|{app_secret}",
            },
        ).get("data", {})

        if (
            debug_payload.get("is_valid") is not True
            or str(debug_payload.get("app_id") or "") != str(app_id)
            or not debug_payload.get("user_id")
        ):
            raise serializers.ValidationError(
                {"detail": "Facebook returned an invalid sign-in token."}
            )

        app_secret_proof = hmac.new(
            app_secret.encode(),
            access_token.encode(),
            hashlib.sha256,
        ).hexdigest()
        identity = self._graph_request(
            "me",
            {
                "fields": "id,name,email,first_name,last_name,picture.type(large)",
                "access_token": access_token,
                "appsecret_proof": app_secret_proof,
            },
        )

        subject = str(identity.get("id") or "").strip()
        email = str(identity.get("email") or "").strip().lower()

        if subject != str(debug_payload["user_id"]) or not email:
            raise serializers.ValidationError(
                {
                    "detail": (
                        "Facebook did not provide an email address. "
                        "Allow email access and try again."
                    )
                }
            )

        attrs["identity"] = {
            "sub": subject,
            "email": email,
            "name": str(identity.get("name") or "").strip(),
            "given_name": str(identity.get("first_name") or "").strip(),
            "family_name": str(identity.get("last_name") or "").strip(),
            "picture": identity.get("picture"),
        }
        return attrs


class QOTTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        rotated_token = data.get("refresh")

        if not rotated_token:
            return data

        refresh = RefreshToken(rotated_token)

        if refresh.get("keep_signed_in"):
            refresh.set_exp(lifetime=settings.KEEP_SIGNED_IN_LIFETIME)
            data["refresh"] = str(refresh)

        return data


class ProfileUpdateSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(required=False)
    avatar = serializers.ImageField(write_only=True, required=False, allow_null=True)
    cover_photo = serializers.ImageField(write_only=True, required=False, allow_null=True)
    bio = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    business_name = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=150,
    )
    default_city = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.filter(is_active=True),
        write_only=True,
        required=False,
        allow_null=True,
    )
    timezone = serializers.CharField(
        write_only=True,
        required=False,
        max_length=64,
    )

    class Meta:
        model = User
        fields = [
            "phone",
            "email",
            "full_name",
            "profile",
            "avatar",
            "cover_photo",
            "bio",
            "business_name",
            "default_city",
            "timezone",
        ]
        read_only_fields = ["email"]

    def validate_avatar(self, value):
        return self._validate_profile_image(value)

    def validate_cover_photo(self, value):
        return self._validate_profile_image(value)

    def validate_timezone(self, value):
        return validate_timezone_name(value)

    def validate_phone(self, value):
        if not value:
            return value

        try:
            normalized_phone = normalize_ugandan_phone(value)
        except ValueError as error:
            raise serializers.ValidationError(str(error)) from error

        duplicate = User.objects.filter(phone=normalized_phone)

        if self.instance:
            duplicate = duplicate.exclude(pk=self.instance.pk)

        if duplicate.exists():
            raise serializers.ValidationError(
                "An account with this phone number already exists."
            )

        return normalized_phone

    def _validate_profile_image(self, value):
        if value is None:
            return value

        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Image must be 5MB or smaller.")

        content_type = getattr(value, "content_type", "")
        if content_type and content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise serializers.ValidationError("Use a JPG, PNG, or WEBP image.")

        return value

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", None)
        flat_profile_data = {
            field: validated_data.pop(field)
            for field in [
                "avatar",
                "cover_photo",
                "bio",
                "business_name",
                "default_city",
                "timezone",
            ]
            if field in validated_data
        }

        previous_phone = instance.phone
        instance.phone = validated_data.get("phone", instance.phone)
        instance.full_name = validated_data.get("full_name", instance.full_name)

        if instance.phone != previous_phone:
            instance.phone_verified_at = None

            if not instance.email_verified:
                instance.is_verified = False

        instance.save()

        if profile_data is not None or flat_profile_data:
            profile, _ = UserProfile.objects.get_or_create(user=instance)

            for field, value in {
                **(profile_data or {}),
                **flat_profile_data,
            }.items():
                setattr(profile, field, value)

            profile.save()
            instance._state.fields_cache.pop("profile", None)

        return instance
    

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        user = User.objects.filter(email__iexact=value, is_active=True).first()

        # Do not reveal whether an email exists or not.
        self.context["user"] = user

        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        uid = attrs.get("uid")
        token = attrs.get("token")
        new_password = attrs.get("new_password")
        new_password_confirm = attrs.get("new_password_confirm")

        if new_password != new_password_confirm:
            raise serializers.ValidationError(
                {"new_password_confirm": "Passwords do not match."}
            )

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id, is_active=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError("Invalid password reset link.")

        if not default_token_generator.check_token(user, token):
            raise serializers.ValidationError("Invalid or expired password reset token.")

        attrs["user"] = user
        return attrs

    def save(self):
        user = self.validated_data["user"]
        new_password = self.validated_data["new_password"]

        user.set_password(new_password)
        user.save(update_fields=["password"])

        return user
    
class SendVerificationCodeSerializer(serializers.Serializer):
    channel = serializers.ChoiceField(
        choices=[
            VerificationCode.CHANNEL_PHONE,
            VerificationCode.CHANNEL_EMAIL,
        ],
        default=VerificationCode.CHANNEL_PHONE,
    )


class ConfirmVerificationCodeSerializer(serializers.Serializer):
    channel = serializers.ChoiceField(
        choices=[
            VerificationCode.CHANNEL_PHONE,
            VerificationCode.CHANNEL_EMAIL,
        ],
        default=VerificationCode.CHANNEL_PHONE,
    )
    code = serializers.RegexField(
        regex=r"^\d{6}$",
        error_messages={
            "invalid": "Enter the 6-digit verification code.",
        },
    )
    
