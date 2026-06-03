from django.contrib import admin

from .models import ChatThread, ChatMessage


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = [
        "sender",
        "message_type",
        "body",
        "image",
        "is_read",
        "read_at",
        "created_at",
    ]
    can_delete = False


@admin.register(ChatThread)
class ChatThreadAdmin(admin.ModelAdmin):
    list_display = [
        "listing",
        "buyer",
        "seller",
        "last_message_at",
        "buyer_unread_count",
        "seller_unread_count",
        "is_active",
        "created_at",
    ]

    list_filter = [
        "is_active",
        "created_at",
        "last_message_at",
    ]

    search_fields = [
        "listing__title",
        "buyer__phone",
        "buyer__email",
        "buyer__full_name",
        "seller__phone",
        "seller__email",
        "seller__full_name",
        "last_message",
    ]

    readonly_fields = [
        "created_at",
        "last_message_at",
    ]

    inlines = [
        ChatMessageInline,
    ]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = [
        "thread",
        "sender",
        "message_type",
        "is_read",
        "created_at",
    ]

    list_filter = [
        "message_type",
        "is_read",
        "created_at",
    ]

    search_fields = [
        "body",
        "sender__phone",
        "sender__email",
        "sender__full_name",
        "thread__listing__title",
    ]

    readonly_fields = [
        "created_at",
        "read_at",
    ]