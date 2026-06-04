from django.conf import settings
from django.db import models


class Notification(models.Model):
    TYPE_MESSAGE = "message"
    TYPE_LISTING_APPROVED = "listing_approved"
    TYPE_LISTING_REJECTED = "listing_rejected"
    TYPE_LISTING_EXPIRED = "listing_expired"
    TYPE_SYSTEM = "system"

    TYPE_CHOICES = [
        (TYPE_MESSAGE, "New Message"),
        (TYPE_LISTING_APPROVED, "Listing Approved"),
        (TYPE_LISTING_REJECTED, "Listing Rejected"),
        (TYPE_LISTING_EXPIRED, "Listing Expired"),
        (TYPE_SYSTEM, "System"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    notification_type = models.CharField(
        max_length=50,
        choices=TYPE_CHOICES,
        db_index=True,
    )

    title = models.CharField(max_length=150)
    message = models.TextField()

    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )

    chat_thread = models.ForeignKey(
        "chats.ChatThread",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )

    is_read = models.BooleanField(default=False, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["notification_type"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.title}"