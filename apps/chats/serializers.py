from rest_framework import serializers

from apps.listings.models import Listing
from apps.listings.serializers import ListingListSerializer

from .models import ChatThread, ChatMessage


class ChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.full_name", read_only=True)
    sender_phone = serializers.CharField(source="sender.phone", read_only=True)

    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "thread",
            "sender",
            "sender_name",
            "sender_phone",
            "message_type",
            "body",
            "image",
            "is_read",
            "read_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "thread",
            "sender",
            "is_read",
            "read_at",
            "created_at",
        ]


class ChatThreadSerializer(serializers.ModelSerializer):
    listing = ListingListSerializer(read_only=True)
    buyer_name = serializers.CharField(source="buyer.full_name", read_only=True)
    seller_name = serializers.CharField(source="seller.full_name", read_only=True)
    unread_count = serializers.SerializerMethodField()

    other_user_name = serializers.SerializerMethodField()
    other_user_phone = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatThread
        fields = [
            "id",
            "listing",
            "buyer",
            "buyer_name",
            "seller",
            "seller_name",
            "unread_count",
            "other_user_name",
            "other_user_phone",
            "last_message",
            "last_message_at",
            "buyer_unread_count",
            "seller_unread_count",
            "unread_count",
            "is_active",
            "created_at",
        ]

    def get_other_user_name(self, obj):
        request = self.context.get("request")

        if not request:
            return None

        if request.user == obj.buyer:
            return obj.seller.full_name

        return obj.buyer.full_name

    def get_other_user_phone(self, obj):
        request = self.context.get("request")

        if not request:
            return None

        if request.user == obj.buyer:
            return obj.seller.phone

        return obj.buyer.phone

    def get_unread_count(self, obj):
        request = self.context.get("request")

        if not request:
            return 0

        if request.user == obj.buyer:
            return obj.buyer_unread_count

        return obj.seller_unread_count
    
    def get_unread_count(self, obj):
        if hasattr(obj, "unread_count_value"):
            return obj.unread_count_value

        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return 0

        return obj.messages.filter(
            is_read=False,
        ).exclude(
            sender=request.user,
        ).count()


class ChatThreadCreateSerializer(serializers.Serializer):
    listing_id = serializers.IntegerField()

    def validate_listing_id(self, value):
        try:
            listing = Listing.objects.select_related("seller").get(
                pk=value,
                status=Listing.STATUS_ACTIVE,
            )
        except Listing.DoesNotExist:
            raise serializers.ValidationError("Active listing not found.")

        request = self.context["request"]

        if listing.seller == request.user:
            raise serializers.ValidationError(
                "You cannot start a chat on your own listing."
            )

        self.context["listing"] = listing

        return value


class ChatMessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = [
            "message_type",
            "body",
            "image",
        ]

    def validate(self, attrs):
        message_type = attrs.get("message_type", ChatMessage.TYPE_TEXT)
        body = attrs.get("body")
        image = attrs.get("image")

        if message_type == ChatMessage.TYPE_TEXT and not body:
            raise serializers.ValidationError(
                {"body": "Text message body is required."}
            )

        if message_type == ChatMessage.TYPE_IMAGE and not image:
            raise serializers.ValidationError(
                {"image": "Image is required for image messages."}
            )

        return attrs