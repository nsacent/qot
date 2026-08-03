from django.contrib import admin

from .models import AdminActivityLog, AdminPushBroadcast


@admin.register(AdminActivityLog)
class AdminActivityLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "actor_name",
        "action",
        "target_type",
        "status_code",
        "platform",
    )
    list_filter = ("actor_role", "action", "status_code", "platform")
    search_fields = ("actor_name", "actor_email", "description", "target_id")
    readonly_fields = [field.name for field in AdminActivityLog._meta.fields]


@admin.register(AdminPushBroadcast)
class AdminPushBroadcastAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "title",
        "audience",
        "matched_users",
        "accepted_devices",
        "created_by",
    )
    list_filter = ("audience", "delivery_type", "created_at")
    search_fields = ("title", "message", "created_by__full_name")
    readonly_fields = [field.name for field in AdminPushBroadcast._meta.fields]
