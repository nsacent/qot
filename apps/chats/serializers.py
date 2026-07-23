from rest_framework import serializers

from apps.listings.models import Listing
from apps.listings.serializers import ListingListSerializer

from .models import (
    ChatThread,
    ChatMessage,
    ChatMessageAttachment,
    ChatBlock,
    ChatReport,
)

class ChatMessageAttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessageAttachment
        fields = [
            "id",
            "file",
            "file_url",
            "file_type",
            "original_name",
            "size",
            "created_at",
        ]
        read_only_fields = fields

    def get_file_url(self, obj):
        request = self.context.get("request")

        if not obj.file:
            return None

        if request:
            return request.build_absolute_uri(obj.file.url)

        return obj.file.url
    

class ChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.full_name", read_only=True)
    sender_phone = serializers.CharField(source="sender.phone", read_only=True)
    attachments = ChatMessageAttachmentSerializer(many=True, read_only=True)

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
            "attachments",
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
    other_user_avatar = serializers.SerializerMethodField()
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
            "other_user_avatar",
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

    def get_other_user_avatar(self, obj):
        request = self.context.get("request")

        if not request:
            return None

        other_user = obj.seller if request.user == obj.buyer else obj.buyer
        profile = getattr(other_user, "profile", None)

        if not profile or not profile.avatar:
            return None

        return request.build_absolute_uri(profile.avatar.url)

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
    initial_message = serializers.CharField(
        required=False,
        allow_blank=False,
        max_length=1000,
        trim_whitespace=True,
    )

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



class ChatAttachmentUploadSerializer(serializers.Serializer):
    message = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
    )

    file = serializers.FileField()

    def validate_file(self, file):
        max_size = 10 * 1024 * 1024

        if file.size > max_size:
            raise serializers.ValidationError(
                "Attachment size cannot exceed 10MB."
            )

        allowed_extensions = [
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".gif",
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".ppt",
            ".pptx",
            ".txt",
            ".csv",
        ]

        file_name = file.name.lower()

        if not any(file_name.endswith(ext) for ext in allowed_extensions):
            raise serializers.ValidationError(
                "This file type is not supported. Attach an image, PDF, Office document, TXT, or CSV file."
            )

        return file
    

class ChatBlockSerializer(serializers.ModelSerializer):
    blocked_user_name = serializers.CharField(
        source="blocked_user.full_name",
        read_only=True,
    )

    class Meta:
        model = ChatBlock
        fields = [
            "id",
            "blocker",
            "blocked_user",
            "blocked_user_name",
            "thread",
            "reason",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "blocker",
            "blocked_user",
            "blocked_user_name",
            "thread",
            "is_active",
            "created_at",
            "updated_at",
        ]


class ChatBlockCreateSerializer(serializers.Serializer):
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
    )


class ChatReportCreateSerializer(serializers.Serializer):
    reason = serializers.ChoiceField(
        choices=ChatReport.REASON_CHOICES,
        default=ChatReport.REASON_OTHER,
    )

    description = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
    )


class ChatReportSerializer(serializers.ModelSerializer):
    reporter_name = serializers.CharField(
        source="reporter.full_name",
        read_only=True,
    )
    reported_user_name = serializers.CharField(
        source="reported_user.full_name",
        read_only=True,
    )

    class Meta:
        model = ChatReport
        fields = [
            "id",
            "thread",
            "reporter",
            "reporter_name",
            "reported_user",
            "reported_user_name",
            "reason",
            "description",
            "is_resolved",
            "resolved_by",
            "resolved_at",
            "created_at",
        ]
        read_only_fields = fields
