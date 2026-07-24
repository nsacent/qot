from django.urls import reverse
from rest_framework import serializers

from apps.listings.models import Listing
from apps.listings.serializers import ListingListSerializer

from .models import (
    ChatThread,
    ChatMessage,
    ChatMessageAttachment,
    ChatBlock,
    ChatReport,
    ChatThreadParticipantState,
)
from .presence import is_user_online


class ChatMessageAttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessageAttachment
        fields = [
            "id",
            "file_url",
            "file_type",
            "original_name",
            "size",
            "created_at",
        ]
        read_only_fields = fields

    def get_file_url(self, obj):
        if not obj.file:
            return None

        return reverse(
            "chats:chat_attachment_download",
            kwargs={"pk": obj.pk},
        )
    

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
    other_user_id = serializers.SerializerMethodField()
    other_user_name = serializers.SerializerMethodField()
    other_user_phone = serializers.SerializerMethodField()
    other_user_avatar = serializers.SerializerMethodField()
    other_user_online = serializers.SerializerMethodField()
    other_user_last_seen = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    is_favourite = serializers.SerializerMethodField()
    is_archived = serializers.SerializerMethodField()
    is_spam = serializers.SerializerMethodField()
    is_marked_unread = serializers.SerializerMethodField()

    class Meta:
        model = ChatThread
        fields = [
            "id",
            "listing",
            "buyer",
            "buyer_name",
            "seller",
            "seller_name",
            "other_user_id",
            "other_user_name",
            "other_user_phone",
            "other_user_avatar",
            "other_user_online",
            "other_user_last_seen",
            "last_message",
            "last_message_at",
            "buyer_unread_count",
            "seller_unread_count",
            "unread_count",
            "is_favourite",
            "is_archived",
            "is_spam",
            "is_marked_unread",
            "is_active",
            "created_at",
        ]

    def _other_user(self, obj):
        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return None

        return obj.seller if request.user == obj.buyer else obj.buyer

    def _participant_state(self, obj):
        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return None

        cache = getattr(self, "_participant_state_cache", {})

        if obj.pk not in cache:
            cache[obj.pk] = ChatThreadParticipantState.objects.filter(
                thread=obj,
                user=request.user,
            ).first()
            self._participant_state_cache = cache

        return cache[obj.pk]

    def _state_value(self, obj, annotation, field):
        if hasattr(obj, annotation):
            return bool(getattr(obj, annotation))

        state = self._participant_state(obj)
        return bool(state and getattr(state, field))

    def get_other_user_id(self, obj):
        user = self._other_user(obj)
        return user.id if user else None

    def get_other_user_name(self, obj):
        user = self._other_user(obj)
        return user.full_name if user else None

    def get_other_user_phone(self, obj):
        user = self._other_user(obj)
        return user.phone if user else None

    def get_other_user_avatar(self, obj):
        request = self.context.get("request")
        other_user = self._other_user(obj)

        if not request or not other_user:
            return None

        profile = getattr(other_user, "profile", None)

        if not profile or not profile.avatar:
            return None

        return request.build_absolute_uri(profile.avatar.url)

    def get_unread_count(self, obj):
        if hasattr(obj, "unread_count_value"):
            return obj.unread_count_value

        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return 0

        if request.user == obj.buyer:
            return obj.buyer_unread_count

        return obj.seller_unread_count

    def get_other_user_online(self, obj):
        user = self._other_user(obj)
        return is_user_online(user.id) if user else False

    def get_other_user_last_seen(self, obj):
        user = self._other_user(obj)

        if not user:
            return None

        return user.last_seen_at or user.last_login or user.updated_at

    def get_is_favourite(self, obj):
        return self._state_value(obj, "user_is_favourite", "is_favourite")

    def get_is_archived(self, obj):
        return self._state_value(obj, "user_is_archived", "is_archived")

    def get_is_spam(self, obj):
        return self._state_value(obj, "user_is_spam", "is_spam")

    def get_is_marked_unread(self, obj):
        return self._state_value(obj, "user_marked_unread", "is_marked_unread")


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


class ChatThreadStateUpdateSerializer(serializers.Serializer):
    is_favourite = serializers.BooleanField(required=False)
    is_archived = serializers.BooleanField(required=False)
    is_spam = serializers.BooleanField(required=False)
    is_marked_unread = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "Choose at least one chat setting to update."
            )

        return attrs


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
