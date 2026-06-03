from django.conf import settings
from django.db import models
from django.utils import timezone


class ChatThread(models.Model):
    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.CASCADE,
        related_name="chat_threads",
    )

    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="buyer_threads",
    )

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="seller_threads",
    )

    last_message = models.TextField(null=True, blank=True)
    last_message_at = models.DateTimeField(null=True, blank=True)

    buyer_unread_count = models.PositiveIntegerField(default=0)
    seller_unread_count = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["listing", "buyer", "seller"]
        ordering = ["-last_message_at", "-created_at"]
        indexes = [
            models.Index(fields=["buyer", "last_message_at"]),
            models.Index(fields=["seller", "last_message_at"]),
            models.Index(fields=["listing"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.buyer} ↔ {self.seller} - {self.listing}"


class ChatMessage(models.Model):
    TYPE_TEXT = "text"
    TYPE_IMAGE = "image"

    TYPE_CHOICES = [
        (TYPE_TEXT, "Text"),
        (TYPE_IMAGE, "Image"),
    ]

    thread = models.ForeignKey(
        ChatThread,
        on_delete=models.CASCADE,
        related_name="messages",
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_chat_messages",
    )

    message_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_TEXT,
    )

    body = models.TextField(null=True, blank=True)

    image = models.ImageField(
        upload_to="chats/images/",
        null=True,
        blank=True,
    )

    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["thread", "created_at"]),
            models.Index(fields=["sender", "created_at"]),
            models.Index(fields=["is_read"]),
        ]

    def __str__(self):
        return f"Message from {self.sender}"

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])