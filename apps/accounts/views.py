from smtplib import SMTPException

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import User
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    GoogleLoginSerializer,
    UserSerializer,
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


def get_tokens_for_user(user, keep_signed_in=False):
    refresh = RefreshToken.for_user(user)

    if keep_signed_in:
        refresh["keep_signed_in"] = True
        refresh.set_exp(lifetime=settings.KEEP_SIGNED_IN_LIFETIME)

    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class RegisterAPIView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()
        tokens = get_tokens_for_user(user)

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
        )

        return Response(
            {
                "message": "Login successful.",
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
                f"{settings.FRONTEND_URL}/account/reset-password"
                f"?uid={uid}&token={token}"
            )

            send_mail(
                subject="Reset your QOT password",
                message=(
                    "You requested a password reset.\n\n"
                    f"Use this link to reset your password:\n{reset_link}\n\n"
                    "If you did not request this, you can ignore this email."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
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
