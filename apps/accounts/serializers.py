from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from .models import User, UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            "avatar",
            "bio",
            "business_name",
            "notification_preferences",
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


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "phone",
            "email",
            "full_name",
            "role",
            "is_verified",
            "is_banned",
            "date_joined",
            "profile",
        ]
        read_only_fields = [
            "id",
            "role",
            "is_verified",
            "is_banned",
            "date_joined",
        ]


class RegisterSerializer(serializers.ModelSerializer):
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
        identifier = attrs.get("identifier")
        password = attrs.get("password")

        user = None

        if identifier:
            user = User.objects.filter(phone=identifier).first()

            if user is None:
                user = User.objects.filter(email__iexact=identifier).first()

        if user is None:
            raise serializers.ValidationError("Invalid login credentials.")

        if not user.check_password(password):
            raise serializers.ValidationError("Invalid login credentials.")

        if not user.is_active:
            raise serializers.ValidationError("This account is inactive.")

        if user.is_banned:
            raise serializers.ValidationError("This account has been banned.")

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

    class Meta:
        model = User
        fields = [
            "phone",
            "email",
            "full_name",
            "profile",
        ]

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", None)

        instance.phone = validated_data.get("phone", instance.phone)
        instance.email = validated_data.get("email", instance.email)
        instance.full_name = validated_data.get("full_name", instance.full_name)
        instance.save()

        if profile_data:
            profile, _ = UserProfile.objects.get_or_create(user=instance)

            for field, value in profile_data.items():
                setattr(profile, field, value)

            profile.save()

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
        choices=["email"],
        default="email",
    )


class ConfirmVerificationCodeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=10)
    
