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
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["actor", "-created_at"], name="adminlog_actor_created_idx"),
            models.Index(fields=["action", "-created_at"], name="adminlog_action_created_idx"),
        ]

    def __str__(self):
        return f"{self.actor_name or 'Staff'}: {self.description}"
