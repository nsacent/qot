from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from .managers import UserManager


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
    is_banned = models.BooleanField(default=False)

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

    def __str__(self):
        return self.phone or self.email or self.full_name


class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    avatar = models.ImageField(upload_to="users/avatars/", null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    business_name = models.CharField(max_length=150, null=True, blank=True)

    trust_score = models.PositiveIntegerField(default=0)
    total_listings = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile: {self.user}"
    

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

    code = models.CharField(max_length=10)

    is_used = models.BooleanField(default=False)

    expires_at = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "purpose", "is_used"]),
            models.Index(fields=["code"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.purpose}"

    def is_expired(self):
        return timezone.now() > self.expires_at