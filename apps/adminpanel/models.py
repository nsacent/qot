from django.conf import settings
from django.db import models


class AdminActivityLog(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="admin_activity_logs",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    actor_name = models.CharField(max_length=180, blank=True)
    actor_email = models.EmailField(blank=True)
    actor_role = models.CharField(max_length=20, blank=True, db_index=True)
    action = models.CharField(max_length=120, db_index=True)
    description = models.CharField(max_length=255)
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=500)
    target_type = models.CharField(max_length=80, blank=True, db_index=True)
    target_id = models.CharField(max_length=180, blank=True)
    status_code = models.PositiveSmallIntegerField(db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    platform = models.CharField(max_length=20, default="unknown", db_index=True)
    user_agent = models.CharField(max_length=500, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["actor", "-created_at"], name="adminlog_actor_created_idx"),
            models.Index(fields=["action", "-created_at"], name="adminlog_action_created_idx"),
        ]

    def __str__(self):
        return f"{self.actor_name or 'User'}: {self.description}"


class AdminPushBroadcast(models.Model):
    AUDIENCE_ALL = "all"
    AUDIENCE_ANDROID = "android"
    AUDIENCE_IOS = "ios"
    AUDIENCE_SELECTED = "selected"
    AUDIENCE_CHOICES = [
        (AUDIENCE_ALL, "All users"),
        (AUDIENCE_ANDROID, "Android users"),
        (AUDIENCE_IOS, "iOS users"),
        (AUDIENCE_SELECTED, "Selected users"),
    ]

    DELIVERY_ANNOUNCEMENT = "announcement"
    DELIVERY_MARKETING = "marketing"
    DELIVERY_CHOICES = [
        (DELIVERY_ANNOUNCEMENT, "Service announcement"),
        (DELIVERY_MARKETING, "Marketing"),
    ]

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="admin_push_broadcasts",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    title = models.CharField(max_length=150)
    message = models.TextField()
    audience = models.CharField(max_length=20, choices=AUDIENCE_CHOICES)
    delivery_type = models.CharField(
        max_length=20,
        choices=DELIVERY_CHOICES,
        default=DELIVERY_ANNOUNCEMENT,
    )
    action_url = models.CharField(max_length=500, blank=True)
    image = models.ImageField(
        upload_to="admin/push-notifications/%Y/%m/",
        blank=True,
    )
    selected_user_ids = models.JSONField(default=list, blank=True)
    matched_users = models.PositiveIntegerField(default=0)
    targeted_devices = models.PositiveIntegerField(default=0)
    accepted_devices = models.PositiveIntegerField(default=0)
    rejected_devices = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.title} ({self.get_audience_display()})"
