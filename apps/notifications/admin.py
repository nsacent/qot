from django.contrib import admin

from .models import Notification, PushDevice


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "notification_type",
        "title",
        "is_read",
        "created_at",
    ]

    list_filter = [
        "notification_type",
        "is_read",
        "created_at",
    ]

    search_fields = [
        "user__phone",
        "user__email",
        "user__full_name",
        "title",
        "message",
    ]

    readonly_fields = [
        "created_at",
    ]


@admin.register(PushDevice)
class PushDeviceAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "platform",
        "is_active",
        "last_registered_at",
    ]
    list_filter = ["platform", "is_active"]
    search_fields = ["user__phone", "user__email", "expo_push_token"]
    readonly_fields = ["created_at", "last_registered_at"]
