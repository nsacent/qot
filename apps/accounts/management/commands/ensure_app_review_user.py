import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User


class Command(BaseCommand):
    help = "Create or refresh the ordinary, pre-verified App Store review account."

    EMAIL = "appreview@qot.ug"
    PHONE = "+256700000000"
    FULL_NAME = "QOT App Reviewer"

    @transaction.atomic
    def handle(self, *args, **options):
        password = os.environ.get("QOT_APP_REVIEW_PASSWORD", "")
        if len(password) < 16:
            raise CommandError(
                "QOT_APP_REVIEW_PASSWORD must be set to at least 16 characters."
            )

        conflicting_phone = User.objects.filter(phone=self.PHONE).exclude(
            email__iexact=self.EMAIL
        )
        if conflicting_phone.exists():
            raise CommandError(
                "The App Store review phone placeholder is already in use."
            )

        user = User.objects.filter(email__iexact=self.EMAIL).first()
        created = user is None
        if created:
            user = User(email=self.EMAIL)

        verified_at = timezone.now()
        user.phone = self.PHONE
        user.email = self.EMAIL
        user.full_name = self.FULL_NAME
        user.role = User.ROLE_USER
        user.is_active = True
        user.is_frozen = False
        user.frozen_at = None
        user.is_staff = False
        user.is_superuser = False
        user.is_verified = True
        user.phone_verified_at = verified_at
        user.email_verified_at = verified_at
        user.is_banned = False
        user.banned_reason = None
        user.set_password(password)
        user.save()

        action = "created" if created else "refreshed"
        self.stdout.write(
            self.style.SUCCESS(f"App Store review account {action}: {self.EMAIL}")
        )
