import math
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import VerificationCode
from .sms import send_sms


class OTPRateLimitError(RuntimeError):
    def __init__(self, message, retry_after):
        super().__init__(message)
        self.retry_after = max(1, int(retry_after))


def generate_otp_code():
    return f"{secrets.randbelow(1_000_000):06d}"


def mask_phone(phone):
    value = str(phone or "")

    if len(value) < 7:
        return value

    return f"{value[:4]} ••• ••{value[-2:]}"


def mask_email(email):
    value = str(email or "").strip()

    if "@" not in value:
        return value

    local, domain = value.rsplit("@", 1)
    visible = local[:2] if len(local) > 1 else local[:1]
    return f"{visible}{'•' * max(3, len(local) - len(visible))}@{domain}"


def _verification_queryset(user, channel):
    return VerificationCode.objects.filter(
        user=user,
        purpose=VerificationCode.PURPOSE_ACCOUNT_VERIFICATION,
        channel=channel,
    )


def _enforce_send_limits(user, channel):
    now = timezone.now()
    resend_seconds = max(1, int(settings.PHONE_OTP_RESEND_SECONDS))
    max_hourly_sends = max(1, int(settings.PHONE_OTP_MAX_SENDS_PER_HOUR))
    codes = _verification_queryset(user, channel)
    latest = codes.order_by("-created_at").first()

    if latest:
        elapsed = (now - latest.created_at).total_seconds()

        if elapsed < resend_seconds:
            retry_after = math.ceil(resend_seconds - elapsed)
            raise OTPRateLimitError(
                f"Please wait {retry_after} seconds before requesting another code.",
                retry_after,
            )

    sent_last_hour = codes.filter(created_at__gte=now - timedelta(hours=1)).count()

    if sent_last_hour >= max_hourly_sends:
        oldest_recent = (
            codes
            .filter(created_at__gte=now - timedelta(hours=1))
            .order_by("created_at")
            .first()
        )
        retry_after = 3600

        if oldest_recent:
            retry_after = math.ceil(
                3600 - (now - oldest_recent.created_at).total_seconds()
            )

        raise OTPRateLimitError(
            "Too many verification codes requested. Please try again later.",
            retry_after,
        )


def _store_verification_code(user, channel, code):
    with transaction.atomic():
        _verification_queryset(user, channel).filter(is_used=False).update(
            is_used=True
        )

        return VerificationCode.objects.create(
            user=user,
            purpose=VerificationCode.PURPOSE_ACCOUNT_VERIFICATION,
            channel=channel,
            code=make_password(code),
            expires_at=(
                timezone.now()
                + timedelta(minutes=max(1, int(settings.PHONE_OTP_EXPIRY_MINUTES)))
            ),
        )


def create_phone_verification_code(user):
    if not user.phone:
        raise ValueError("A phone number is required for verification.")

    _enforce_send_limits(user, VerificationCode.CHANNEL_PHONE)

    code = generate_otp_code()
    expiry_minutes = max(1, int(settings.PHONE_OTP_EXPIRY_MINUTES))
    message = (
        f"Your QOT Uganda verification code is {code}. "
        f"It expires in {expiry_minutes} minutes. Do not share this code."
    )

    send_sms(user.phone, message)

    return _store_verification_code(
        user,
        VerificationCode.CHANNEL_PHONE,
        code,
    )


def create_email_verification_code(user):
    if not user.email:
        raise ValueError("An email address is required for verification.")

    _enforce_send_limits(user, VerificationCode.CHANNEL_EMAIL)

    code = generate_otp_code()
    expiry_minutes = max(1, int(settings.PHONE_OTP_EXPIRY_MINUTES))

    send_mail(
        subject="Verify your QOT account",
        message=(
            f"Hello {user.full_name},\n\n"
            f"Your QOT verification code is: {code}\n\n"
            f"This code expires in {expiry_minutes} minutes.\n\n"
            "If you did not request this, please ignore this message."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )

    return _store_verification_code(
        user,
        VerificationCode.CHANNEL_EMAIL,
        code,
    )


def _verify_code(user, code, channel):
    verification = (
        _verification_queryset(user, channel)
        .filter(is_used=False)
        .order_by("-created_at")
        .first()
    )

    if not verification:
        return False, "Invalid verification code."

    if verification.is_expired():
        verification.is_used = True
        verification.save(update_fields=["is_used"])
        return False, "Verification code has expired. Request a new code."

    max_attempts = max(1, int(settings.PHONE_OTP_MAX_ATTEMPTS))

    if verification.failed_attempts >= max_attempts:
        verification.is_used = True
        verification.save(update_fields=["is_used"])
        return False, "Too many incorrect attempts. Request a new code."

    if not check_password(str(code), verification.code):
        verification.failed_attempts += 1
        update_fields = ["failed_attempts"]

        if verification.failed_attempts >= max_attempts:
            verification.is_used = True
            update_fields.append("is_used")

        verification.save(update_fields=update_fields)

        if verification.is_used:
            return False, "Too many incorrect attempts. Request a new code."

        remaining = max_attempts - verification.failed_attempts
        return False, f"Invalid verification code. {remaining} attempts remaining."

    verification.is_used = True
    verification.save(update_fields=["is_used"])

    user.is_verified = True
    update_fields = ["is_verified", "updated_at"]

    if channel == VerificationCode.CHANNEL_PHONE:
        user.phone_verified_at = timezone.now()
        update_fields.append("phone_verified_at")
    else:
        user.email_verified_at = timezone.now()
        update_fields.append("email_verified_at")

    user.save(update_fields=update_fields)

    if channel == VerificationCode.CHANNEL_PHONE:
        return True, "Phone number verified successfully."

    return True, "Email address verified successfully."


def verify_phone_code(user, code):
    return _verify_code(user, code, VerificationCode.CHANNEL_PHONE)


def verify_email_code(user, code):
    return _verify_code(user, code, VerificationCode.CHANNEL_EMAIL)
