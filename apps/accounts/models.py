from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .managers import UserManager
from .phone_numbers import normalize_ugandan_phone


def default_notification_preferences():
    return {
        "verification": True,
        "messages": True,
        "listing_approvals": True,
        "listing_rejections": True,
        "reports": True,
        "renewals": True,
        "marketing": False,
    }


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_USER = "user"
    ROLE_ADMIN = "admin"
    ROLE_MODERATOR = "moderator"

    ROLE_CHOICES = [
        (ROLE_USER, "User"),
        (ROLE_ADMIN, "Admin"),
        (ROLE_MODERATOR, "Moderator"),
    ]

    email = models.EmailField(unique=True, null=True, blank=True)
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)

    full_name = models.CharField(max_length=150)

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_USER)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    phone_verified_at = models.DateTimeField(null=True, blank=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    is_banned = models.BooleanField(default=False)

    google_sub = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        editable=False,
    )

    banned_reason = models.TextField(null=True, blank=True)

    date_joined = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["full_name"]

    objects = UserManager()

    class Meta:
        indexes = [
            models.Index(fields=["phone"]),
            models.Index(fields=["email"]),
            models.Index(fields=["is_active", "is_banned"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(phone__isnull=True)
                    | models.Q(phone__regex=r"^\+2567[0-9]{8}$")
                ),
                name="accounts_user_phone_canonical_ug",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.phone:
            try:
                self.phone = normalize_ugandan_phone(self.phone)
            except ValueError as error:
                raise ValidationError({"phone": str(error)}) from error
        else:
            self.phone = None

        super().save(*args, **kwargs)

    def __str__(self):
        return self.phone or self.email or self.full_name

    @property
    def phone_verified(self):
        return bool(self.phone and self.phone_verified_at)

    @property
    def email_verified(self):
        return bool(self.email and self.email_verified_at)


class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    avatar = models.ImageField(upload_to="users/avatars/", null=True, blank=True)
    cover_photo = models.ImageField(
        upload_to="users/covers/",
        null=True,
        blank=True,
    )
    default_city = models.ForeignKey(
        "locations.City",
        on_delete=models.SET_NULL,
        related_name="default_user_profiles",
        null=True,
        blank=True,
    )
    bio = models.TextField(null=True, blank=True)
    business_name = models.CharField(max_length=150, null=True, blank=True)
    notification_preferences = models.JSONField(
        default=default_notification_preferences,
        blank=True,
    )
    timezone = models.CharField(max_length=64, default="Africa/Kampala")

    trust_score = models.PositiveIntegerField(default=0)
    total_listings = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile: {self.user}"


class UserFollow(models.Model):
    follower = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="following_relationships",
    )
    following = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="follower_relationships",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["follower", "following"],
                name="unique_user_follow",
            ),
            models.CheckConstraint(
                check=~models.Q(follower=models.F("following")),
                name="prevent_self_follow",
            ),
        ]
        indexes = [
            models.Index(fields=["follower", "created_at"]),
            models.Index(fields=["following", "created_at"]),
        ]

    def __str__(self):
        return f"{self.follower} follows {self.following}"
    

class VerificationCode(models.Model):
    PURPOSE_ACCOUNT_VERIFICATION = "account_verification"
    PURPOSE_PASSWORD_RESET = "password_reset"

    PURPOSE_CHOICES = [
        (PURPOSE_ACCOUNT_VERIFICATION, "Account Verification"),
        (PURPOSE_PASSWORD_RESET, "Password Reset"),
    ]

    CHANNEL_EMAIL = "email"
    CHANNEL_PHONE = "phone"

    CHANNEL_CHOICES = [
        (CHANNEL_EMAIL, "Email"),
        (CHANNEL_PHONE, "Phone"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="verification_codes",
    )

    purpose = models.CharField(
        max_length=50,
        choices=PURPOSE_CHOICES,
        default=PURPOSE_ACCOUNT_VERIFICATION,
    )

    channel = models.CharField(
        max_length=20,
        choices=CHANNEL_CHOICES,
        default=CHANNEL_EMAIL,
    )

    code = models.CharField(max_length=128, editable=False)

    is_used = models.BooleanField(default=False)

    failed_attempts = models.PositiveSmallIntegerField(default=0)

    expires_at = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "purpose", "is_used"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.purpose}"

    def is_expired(self):
        return timezone.now() > self.expires_at
