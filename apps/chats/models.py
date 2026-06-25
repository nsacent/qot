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


class ChatMessageAttachment(models.Model):
    FILE_TYPE_IMAGE = "image"
    FILE_TYPE_DOCUMENT = "document"
    FILE_TYPE_OTHER = "other"

    FILE_TYPE_CHOICES = [
        (FILE_TYPE_IMAGE, "Image"),
        (FILE_TYPE_DOCUMENT, "Document"),
        (FILE_TYPE_OTHER, "Other"),
    ]

    message = models.ForeignKey(
        ChatMessage,
        on_delete=models.CASCADE,
        related_name="attachments",
    )

    file = models.FileField(upload_to="chats/attachments/")

    file_type = models.CharField(
        max_length=20,
        choices=FILE_TYPE_CHOICES,
        default=FILE_TYPE_OTHER,
    )

    original_name = models.CharField(max_length=255, blank=True)
    size = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return self.original_name or str(self.file)
    


class ChatBlock(models.Model):
    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_blocks_made",
    )

    blocked_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_blocks_received",
    )

    thread = models.ForeignKey(
        ChatThread,
        on_delete=models.CASCADE,
        related_name="blocks",
        null=True,
        blank=True,
    )

    reason = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["blocker", "blocked_user", "thread"]
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["blocker", "blocked_user"]),
            models.Index(fields=["thread", "is_active"]),
        ]

    def __str__(self):
        return f"{self.blocker} blocked {self.blocked_user}"


class ChatReport(models.Model):
    REASON_SPAM = "spam"
    REASON_SCAM = "scam"
    REASON_ABUSE = "abuse"
    REASON_HARASSMENT = "harassment"
    REASON_OTHER = "other"

    REASON_CHOICES = [
        (REASON_SPAM, "Spam"),
        (REASON_SCAM, "Scam"),
        (REASON_ABUSE, "Abuse"),
        (REASON_HARASSMENT, "Harassment"),
        (REASON_OTHER, "Other"),
    ]

    thread = models.ForeignKey(
        ChatThread,
        on_delete=models.CASCADE,
        related_name="reports",
    )

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_reports_made",
    )

    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_reports_received",
    )

    reason = models.CharField(
        max_length=50,
        choices=REASON_CHOICES,
        default=REASON_OTHER,
    )

    description = models.TextField(blank=True)

    is_resolved = models.BooleanField(default=False)

    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="resolved_chat_reports",
        null=True,
        blank=True,
    )

    resolved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["thread", "-created_at"]),
            models.Index(fields=["reporter", "-created_at"]),
            models.Index(fields=["reported_user", "-created_at"]),
            models.Index(fields=["is_resolved", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.reporter} reported {self.reported_user}"