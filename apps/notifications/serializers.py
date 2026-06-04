from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    listing_title = serializers.CharField(source="listing.title", read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "title",
            "message",
            "listing",
            "listing_title",
            "chat_thread",
            "is_read",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "notification_type",
            "title",
            "message",
            "listing",
            "listing_title",
            "chat_thread",
            "is_read",
            "created_at",
        ]