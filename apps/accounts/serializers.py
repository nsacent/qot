from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.utils import datetime_from_epoch
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from apps.locations.models import Area, City

from .models import User, UserFollow, UserProfile, UserSession, VerificationCode
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
    default_area_name = serializers.CharField(
        source="default_area.name",
        read_only=True,
    )

    class Meta:
        model = UserProfile
        fields = [
            "avatar",
            "cover_photo",
            "bio",
            "business_name",
            "alternative_phone",
            "default_city",
            "default_city_name",
            "default_region_name",
            "default_area",
            "default_area_name",
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
            "favorites",
            "followers",
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

    def validate(self, attrs):
        attrs = super().validate(attrs)
        area = attrs.get("default_area")
        city = attrs.get("default_city")
        if area and city and area.city_id != city.id:
            raise serializers.ValidationError(
                {"default_area": ["Selected area does not belong to the selected city."]}
            )
        if area and not city:
            attrs["default_city"] = area.city
        return attrs

    def validate_timezone(self, value):
        return validate_timezone_name(value)

    def validate_alternative_phone(self, value):
        if not value:
            return None

        try:
            normalized_phone = normalize_ugandan_phone(value)
        except ValueError as error:
            raise serializers.ValidationError(str(error)) from error

        request = self.context.get("request")
        if request and request.user.is_authenticated and request.user.phone == normalized_phone:
            raise serializers.ValidationError(
                "Use a different number from your primary verified phone."
            )

        return normalized_phone


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
            "is_frozen",
            "frozen_at",
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
            "is_frozen",
            "frozen_at",
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


class UserSessionSerializer(serializers.ModelSerializer):
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = UserSession
        fields = [
            "id",
            "device_name",
            "device_model",
            "platform",
            "os_name",
            "os_version",
            "app_version",
            "ip_address",
            "is_current",
            "created_at",
            "last_seen_at",
            "expires_at",
        ]
        read_only_fields = fields

    def get_is_current(self, obj):
        current_session_id = self.context.get("current_session_id")
        current_device_id = self.context.get("current_device_id")
        if current_session_id:
            return str(obj.id) == str(current_session_id)
        return bool(current_device_id and obj.device_id == current_device_id)


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
        default=True,
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

        if user.is_frozen:
            raise PermissionDenied(
                "This account is frozen. Sign in with your phone OTP to reactivate it."
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


class PhoneOTPRequestSerializer(serializers.Serializer):
    phone = serializers.CharField()

    def validate_phone(self, value):
        try:
            return normalize_ugandan_phone(value)
        except ValueError as error:
            raise serializers.ValidationError(str(error)) from error


class PhoneOTPConfirmSerializer(PhoneOTPRequestSerializer):
    code = serializers.RegexField(
        regex=r"^\d{6}$",
        error_messages={"invalid": "Enter the 6-digit code sent to your phone."},
    )


class GoogleLoginSerializer(serializers.Serializer):
    credential = serializers.CharField(write_only=True)
    keep_signed_in = serializers.BooleanField(
        default=True,
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


class QOTTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        original_refresh = RefreshToken(attrs["refresh"])
        original_jti = str(original_refresh.get("jti") or "")
        session_id = original_refresh.get("session_id")

        session = None
        if session_id:
            session = UserSession.objects.filter(
                id=session_id,
                refresh_jti=original_jti,
                is_active=True,
                expires_at__gt=timezone.now(),
            ).first()
            if session is None:
                raise AuthenticationFailed(
                    "This device has been signed out. Please sign in again.",
                    code="device_signed_out",
                )

        data = super().validate(attrs)
        rotated_token = data.get("refresh")

        if not rotated_token:
            return data

        refresh = RefreshToken(rotated_token)

        if original_refresh.get("keep_signed_in"):
            refresh["keep_signed_in"] = True
            refresh.set_exp(lifetime=settings.KEEP_SIGNED_IN_LIFETIME)

        if session:
            refresh["session_id"] = str(session.id)

        final_refresh = str(refresh)
        final_expiry = datetime_from_epoch(refresh["exp"])
        OutstandingToken.objects.filter(jti=refresh["jti"]).update(
            token=final_refresh,
            expires_at=final_expiry,
        )

        if session:
            session.refresh_jti = str(refresh["jti"])
            session.last_seen_at = timezone.now()
            session.expires_at = final_expiry
            session.save(
                update_fields=["refresh_jti", "last_seen_at", "expires_at"]
            )

        data["refresh"] = final_refresh
        data["access"] = str(refresh.access_token)

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
    default_area = serializers.PrimaryKeyRelatedField(
        queryset=Area.objects.filter(is_active=True),
        write_only=True,
        required=False,
        allow_null=True,
    )
    timezone = serializers.CharField(
        write_only=True,
        required=False,
        max_length=64,
    )
    alternative_phone = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=20,
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
            "alternative_phone",
            "default_city",
            "default_area",
            "timezone",
        ]
        read_only_fields = ["email"]

    def validate_avatar(self, value):
        return self._validate_profile_image(value)

    def validate_cover_photo(self, value):
        return self._validate_profile_image(value)

    def validate_timezone(self, value):
        return validate_timezone_name(value)

    def validate_alternative_phone(self, value):
        if not value:
            return None

        try:
            normalized_phone = normalize_ugandan_phone(value)
        except ValueError as error:
            raise serializers.ValidationError(str(error)) from error

        if self.instance and self.instance.phone == normalized_phone:
            raise serializers.ValidationError(
                "Use a different number from your primary verified phone."
            )
        return normalized_phone

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

    def validate(self, attrs):
        attrs = super().validate(attrs)
        area = attrs.get("default_area")
        city = attrs.get("default_city")
        if area and city and area.city_id != city.id:
            raise serializers.ValidationError(
                {"default_area": ["Selected area does not belong to the selected city."]}
            )
        if area and "default_city" not in attrs:
            attrs["default_city"] = area.city
        return attrs

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
                "alternative_phone",
                "default_city",
                "default_area",
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

            next_city = flat_profile_data.get(
                "default_city",
                (profile_data or {}).get("default_city", profile.default_city),
            )
            next_area = flat_profile_data.get(
                "default_area",
                (profile_data or {}).get("default_area", profile.default_area),
            )
            if next_area and next_city and next_area.city_id != next_city.id:
                flat_profile_data["default_area"] = None

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
    
