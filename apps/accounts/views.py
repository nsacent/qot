from smtplib import SMTPException

from rest_framework import generics, permissions, status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.views import APIView

from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.conf import settings
from django.core.validators import validate_ipv46_address
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.utils import datetime_from_epoch

from .models import User, UserSession
from apps.common.emailing import build_branded_email_html
from apps.notifications.models import PushDevice
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    PhoneOTPRequestSerializer,
    PhoneOTPConfirmSerializer,
    GoogleLoginSerializer,
    UserSerializer,
    UserSessionSerializer,
    ProfileUpdateSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    SendVerificationCodeSerializer,
    ConfirmVerificationCodeSerializer,
)

from .services import (
    OTPRateLimitError,
    create_email_verification_code,
    create_phone_verification_code,
    mask_email,
    mask_phone,
    verify_email_code,
    verify_phone_code,
)
from .sms import SMSConfigurationError, SMSDeliveryError


def _client_ip(request):
    forwarded = str(request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
    address = forwarded or str(request.META.get("REMOTE_ADDR") or "").strip()
    if not address:
        return None
    try:
        validate_ipv46_address(address)
    except ValidationError:
        return None
    return address


def _device_metadata(request):
    raw = request.data.get("device") if hasattr(request.data, "get") else None
    device = raw if isinstance(raw, dict) else {}

    def clean(key, maximum):
        return str(device.get(key) or "").strip()[:maximum]

    platform = clean("platform", 20).lower()
    if platform not in dict(UserSession.PLATFORM_CHOICES):
        platform = str(request.headers.get("X-QOT-Platform") or "unknown").lower()
    if platform not in dict(UserSession.PLATFORM_CHOICES):
        platform = UserSession.PLATFORM_UNKNOWN

    return {
        "device_id": clean("id", 255) or str(request.headers.get("X-QOT-Device-ID") or "")[:255],
        "device_name": clean("device_name", 255),
        "device_model": clean("device_model", 255),
        "platform": platform,
        "os_name": clean("os_name", 100),
        "os_version": clean("os_version", 100),
        "app_version": clean("app_version", 50),
        "ip_address": _client_ip(request),
        "user_agent": str(request.META.get("HTTP_USER_AGENT") or "")[:1000],
    }


def _blacklist_session_refresh(session):
    outstanding = OutstandingToken.objects.filter(jti=session.refresh_jti).first()
    if outstanding:
        BlacklistedToken.objects.get_or_create(token=outstanding)


def _revoke_session(session):
    _blacklist_session_refresh(session)
    now = timezone.now()
    session.is_active = False
    session.revoked_at = now
    session.save(update_fields=["is_active", "revoked_at"])
    if session.device_id:
        PushDevice.objects.filter(
            user=session.user,
            device_id=session.device_id,
            is_active=True,
        ).update(is_active=False)


def get_tokens_for_user(user, keep_signed_in=True, request=None):
    refresh = RefreshToken.for_user(user)

    if keep_signed_in:
        refresh["keep_signed_in"] = True
        refresh.set_exp(lifetime=settings.KEEP_SIGNED_IN_LIFETIME)

    if request is not None:
        metadata = _device_metadata(request)
        device_id = metadata["device_id"]
        if device_id:
            previous_sessions = UserSession.objects.filter(
                user=user,
                device_id=device_id,
                is_active=True,
            )
            for previous in previous_sessions:
                _revoke_session(previous)

        session = UserSession.objects.create(
            user=user,
            refresh_jti=str(refresh["jti"]),
            expires_at=datetime_from_epoch(refresh["exp"]),
            **metadata,
        )
        refresh["session_id"] = str(session.id)

    final_refresh = str(refresh)
    OutstandingToken.objects.filter(jti=refresh["jti"]).update(
        token=final_refresh,
        expires_at=datetime_from_epoch(refresh["exp"]),
    )

    return {
        "refresh": final_refresh,
        "access": str(refresh.access_token),
    }


class RegisterAPIView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()
        tokens = get_tokens_for_user(user, keep_signed_in=True, request=request)

        return Response(
            {
                "message": "Account created successfully.",
                "user": UserSerializer(user).data,
                "tokens": tokens,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        tokens = get_tokens_for_user(
            user,
            keep_signed_in=serializer.validated_data["keep_signed_in"],
            request=request,
        )

        return Response(
            {
                "message": "Login successful.",
                "user": UserSerializer(user).data,
                "tokens": tokens,
            },
            status=status.HTTP_200_OK,
        )


class SendPhoneLoginCodeAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PhoneOTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone"]
        user = User.objects.filter(phone=phone).first()

        # Keep the response generic so this endpoint cannot be used to discover
        # whether a phone number has a QOT account.
        if user and (user.is_active or user.is_frozen) and not user.is_banned:
            try:
                create_phone_verification_code(user)
            except OTPRateLimitError as error:
                return Response(
                    {"detail": str(error), "retry_after": error.retry_after},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
            except (SMSConfigurationError, SMSDeliveryError) as error:
                return Response(
                    {"detail": str(error)},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

        return Response(
            {
                "message": "If this phone number has a QOT account, a sign-in code has been sent.",
                "destination": mask_phone(phone),
                "expires_in": int(settings.PHONE_OTP_EXPIRY_MINUTES) * 60,
                "resend_after": int(settings.PHONE_OTP_RESEND_SECONDS),
            },
            status=status.HTTP_200_OK,
        )


class ConfirmPhoneLoginCodeAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PhoneOTPConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.filter(phone=serializer.validated_data["phone"]).first()
        if user is None:
            return Response(
                {"detail": "The phone number or sign-in code is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not user.is_active and not user.is_frozen:
            return Response(
                {"detail": "This account is inactive. Please contact QOT support."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if user.is_banned:
            return Response(
                {"detail": "This account has been banned. Please contact QOT support."},
                status=status.HTTP_403_FORBIDDEN,
            )

        success, message = verify_phone_code(user, serializer.validated_data["code"])
        if not success:
            return Response(
                {"detail": message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reactivated = user.is_frozen
        if reactivated:
            user.is_active = True
            user.is_frozen = False
            user.frozen_at = None
            user.save(update_fields=["is_active", "is_frozen", "frozen_at", "updated_at"])

        tokens = get_tokens_for_user(user, keep_signed_in=True, request=request)
        return Response(
            {
                "message": (
                    "Account reactivated and phone sign-in successful."
                    if reactivated
                    else "Phone sign-in successful."
                ),
                "user": UserSerializer(user).data,
                "tokens": tokens,
            },
            status=status.HTTP_200_OK,
        )


class GoogleLoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        if request.content_type != "application/json":
            return Response(
                {"detail": "Google sign-in requires a JSON request."},
                status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            )

        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        identity = serializer.validated_data["identity"]
        google_sub = str(identity["sub"])
        email = str(identity["email"]).strip().lower()
        full_name = str(identity.get("name") or "").strip()

        if not full_name:
            given_name = str(identity.get("given_name") or "").strip()
            family_name = str(identity.get("family_name") or "").strip()
            full_name = f"{given_name} {family_name}".strip() or email.split("@")[0]

        user = User.objects.filter(google_sub=google_sub).first()
        found_by_email = False

        if user is None:
            user = User.objects.filter(email__iexact=email).first()
            found_by_email = user is not None

        if user and not user.is_active:
            return Response(
                {"detail": "This account is inactive."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if user and user.is_banned:
            return Response(
                {"detail": "This account has been banned."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if found_by_email:
            if user and user.google_sub and user.google_sub != google_sub:
                return Response(
                    {"detail": "This email is linked to another Google account."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            email_domain = email.rsplit("@", 1)[-1]
            google_is_authoritative = email_domain in {
                "gmail.com",
                "googlemail.com",
            } or bool(identity.get("hd"))

            if not google_is_authoritative:
                return Response(
                    {
                        "detail": (
                            "For security, log in with your password before linking "
                            "this Google account."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            user.google_sub = google_sub
            user.is_verified = True
            user.email_verified_at = timezone.now()
            user.save(update_fields=[
                "google_sub",
                "is_verified",
                "email_verified_at",
                "updated_at",
            ])

        if user is None:
            user = User.objects.create_user(
                email=email,
                full_name=full_name,
                password=None,
                google_sub=google_sub,
                is_verified=True,
                email_verified_at=timezone.now(),
            )

        if (
            user.email
            and user.email.lower() == email
            and not user.email_verified
        ):
            user.email_verified_at = timezone.now()
            user.is_verified = True
            user.save(update_fields=[
                "email_verified_at",
                "is_verified",
                "updated_at",
            ])

        tokens = get_tokens_for_user(
            user,
            keep_signed_in=serializer.validated_data["keep_signed_in"],
            request=request,
        )

        return Response(
            {
                "message": "Google sign-in successful.",
                "user": UserSerializer(user).data,
                "tokens": tokens,
            },
            status=status.HTTP_200_OK,
        )


class LogoutAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response(
                {
                    "detail": "Refresh token is required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)
            UserSession.objects.filter(
                user=request.user,
                refresh_jti=str(token.get("jti") or ""),
                is_active=True,
            ).update(is_active=False, revoked_at=timezone.now())
            token.blacklist()

            return Response(
                {
                    "message": "Logout successful."
                },
                status=status.HTTP_200_OK,
            )

        except TokenError:
            return Response(
                {
                    "detail": "Invalid or expired refresh token."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class UserSessionListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        UserSession.objects.filter(
            user=request.user,
            is_active=True,
            expires_at__lte=now,
        ).update(is_active=False, revoked_at=now)
        sessions = UserSession.objects.filter(
            user=request.user,
            is_active=True,
            expires_at__gt=now,
        )
        serializer = UserSessionSerializer(
            sessions,
            many=True,
            context={
                "current_session_id": request.auth.get("session_id") if request.auth else None,
                "current_device_id": request.headers.get("X-QOT-Device-ID", ""),
            },
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class RegisterCurrentSessionAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_value = str(request.data.get("refresh") or "").strip()
        if not refresh_value:
            return Response(
                {"refresh": ["Refresh token is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            old_refresh = RefreshToken(refresh_value)
        except TokenError:
            return Response(
                {"detail": "Your session has expired. Please sign in again."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if str(old_refresh.get("user_id")) != str(request.user.pk):
            raise AuthenticationFailed("This session does not belong to your account.")

        session_id = old_refresh.get("session_id")
        if session_id and UserSession.objects.filter(
            id=session_id,
            user=request.user,
            is_active=True,
        ).exists():
            return Response(
                {"tokens": None, "message": "This device is already tracked."},
                status=status.HTTP_200_OK,
            )

        keep_signed_in = bool(old_refresh.get("keep_signed_in", True))
        old_refresh.blacklist()
        tokens = get_tokens_for_user(
            request.user,
            keep_signed_in=keep_signed_in,
            request=request,
        )
        return Response(
            {"tokens": tokens, "message": "This device is now tracked."},
            status=status.HTTP_200_OK,
        )


class RevokeUserSessionAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, session_id):
        session = UserSession.objects.filter(
            id=session_id,
            user=request.user,
            is_active=True,
        ).first()
        if session is None:
            return Response(
                {"detail": "Signed-in device not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        current_id = request.auth.get("session_id") if request.auth else None
        if current_id and str(current_id) == str(session.id):
            return Response(
                {"detail": "Use Sign out to sign out this device."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        _revoke_session(session)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RevokeOtherUserSessionsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        current_id = request.auth.get("session_id") if request.auth else None
        current_device_id = request.headers.get("X-QOT-Device-ID", "")
        sessions = UserSession.objects.filter(user=request.user, is_active=True)
        if current_id:
            sessions = sessions.exclude(id=current_id)
        elif current_device_id:
            sessions = sessions.exclude(device_id=current_device_id)

        revoked = 0
        for session in sessions:
            _revoke_session(session)
            revoked += 1

        return Response(
            {"message": "Other devices signed out.", "revoked": revoked},
            status=status.HTTP_200_OK,
        )

class PasswordResetRequestAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(
            data=request.data,
            context={},
        )
        serializer.is_valid(raise_exception=True)

        user = serializer.context.get("user")

        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            reset_link = (
                f"{settings.FRONTEND_URL}/reset-password"
                f"?uid={uid}&token={token}"
            )

            email_message = (
                "You requested a password reset.\n\n"
                "Use the button below to reset your password.\n\n"
                "If you did not request this, you can ignore this email."
            )

            send_mail(
                subject="Reset your QOT password",
                message=f"{email_message}\n\nReset password: {reset_link}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
                html_message=build_branded_email_html(
                    title="Reset your QOT password",
                    message=email_message,
                    action_url=reset_link,
                    action_label="Reset password",
                ),
            )

        return Response(
            {
                "message": "If an account with that email exists, a password reset link has been sent."
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "message": "Password reset successful. You can now log in with your new password."
            },
            status=status.HTTP_200_OK,
        )


class MeAPIView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return ProfileUpdateSerializer

        return UserSerializer

    def get_object(self):
        return self.request.user


class FreezeAccountAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.data.get("confirmation") is not True:
            return Response(
                {"confirmation": ["Confirm that you want to freeze this account."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user

        if user.is_staff or user.is_superuser:
            return Response(
                {"detail": "Administrator accounts cannot be frozen here."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = False
        user.is_frozen = True
        user.frozen_at = timezone.now()
        user.save(update_fields=["is_active", "is_frozen", "frozen_at", "updated_at"])

        PushDevice.objects.filter(user=user, is_active=True).update(is_active=False)
        for outstanding_token in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=outstanding_token)
        UserSession.objects.filter(user=user, is_active=True).update(
            is_active=False,
            revoked_at=timezone.now(),
        )

        return Response(
            {
                "message": (
                    "Your QOT account is frozen. Your public profile and ads are hidden. "
                    "Sign in with a phone OTP whenever you want to reactivate it."
                )
            },
            status=status.HTTP_200_OK,
        )
    

class SendVerificationCodeAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = SendVerificationCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        channel = serializer.validated_data["channel"]

        if channel == "phone" and user.phone_verified:
            return Response(
                {"detail": "This phone number is already verified."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if channel == "email" and user.email_verified:
            return Response(
                {"detail": "This email address is already verified."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if channel == "phone" and not user.phone:
            return Response(
                {"detail": "A phone number is required for verification."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if channel == "email" and not user.email:
            return Response(
                {"detail": "An email address is required for verification."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if channel == "phone":
                create_phone_verification_code(user)
            else:
                create_email_verification_code(user)
        except OTPRateLimitError as error:
            return Response(
                {
                    "detail": str(error),
                    "retry_after": error.retry_after,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except (SMSConfigurationError, SMSDeliveryError) as error:
            return Response(
                {"detail": str(error)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except (SMTPException, OSError):
            return Response(
                {"detail": "Email delivery is temporarily unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "message": "Verification code sent successfully.",
                "channel": channel,
                "destination": (
                    mask_phone(user.phone)
                    if channel == "phone"
                    else mask_email(user.email)
                ),
                "expires_in": int(settings.PHONE_OTP_EXPIRY_MINUTES) * 60,
                "resend_after": int(settings.PHONE_OTP_RESEND_SECONDS),
            },
            status=status.HTTP_200_OK,
        )


class ConfirmVerificationCodeAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ConfirmVerificationCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        channel = serializer.validated_data["channel"]
        verify_code = verify_phone_code if channel == "phone" else verify_email_code
        success, message = verify_code(request.user, serializer.validated_data["code"])

        if not success:
            return Response(
                {"detail": message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"message": message},
            status=status.HTTP_200_OK,
        )
