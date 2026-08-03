from rest_framework import serializers

from .models import Notification, PushDevice


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
            "action_url",
            "is_read",
            "created_at",
        ]
        read_only_fields = fields


class PushDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushDevice
        fields = [
            "id",
            "expo_push_token",
            "platform",
            "device_id",
            "is_active",
            "last_registered_at",
        ]
        read_only_fields = [
            "id",
            "is_active",
            "last_registered_at",
        ]

    def validate_expo_push_token(self, value):
        token = str(value or "").strip()
        if not (
            token.startswith("ExponentPushToken[")
            or token.startswith("ExpoPushToken[")
        ) or not token.endswith("]"):
            raise serializers.ValidationError("Enter a valid Expo push token.")
        return token
