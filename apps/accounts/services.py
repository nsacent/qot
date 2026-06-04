import random
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import VerificationCode


def generate_otp_code():
    return str(random.randint(100000, 999999))


def create_email_verification_code(user):
    VerificationCode.objects.filter(
        user=user,
        purpose=VerificationCode.PURPOSE_ACCOUNT_VERIFICATION,
        channel=VerificationCode.CHANNEL_EMAIL,
        is_used=False,
    ).update(is_used=True)

    code = generate_otp_code()

    verification = VerificationCode.objects.create(
        user=user,
        purpose=VerificationCode.PURPOSE_ACCOUNT_VERIFICATION,
        channel=VerificationCode.CHANNEL_EMAIL,
        code=code,
        expires_at=timezone.now() + timedelta(minutes=10),
    )

    send_mail(
        subject="Verify your QOT account",
        message=(
            f"Hello {user.full_name},\n\n"
            f"Your QOT verification code is: {code}\n\n"
            "This code expires in 10 minutes.\n\n"
            "If you did not request this, please ignore this message."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )

    return verification


def verify_email_code(user, code):
    verification = (
        VerificationCode.objects
        .filter(
            user=user,
            purpose=VerificationCode.PURPOSE_ACCOUNT_VERIFICATION,
            channel=VerificationCode.CHANNEL_EMAIL,
            code=code,
            is_used=False,
        )
        .order_by("-created_at")
        .first()
    )

    if not verification:
        return False, "Invalid verification code."

    if verification.is_expired():
        return False, "Verification code has expired."

    verification.is_used = True
    verification.save(update_fields=["is_used"])

    user.is_verified = True
    user.save(update_fields=["is_verified", "updated_at"])

    return True, "Account verified successfully."