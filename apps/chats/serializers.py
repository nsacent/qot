from decimal import Decimal

from django.urls import reverse
from rest_framework import serializers

from apps.listings.models import Listing
from apps.listings.serializers import ListingListSerializer
from apps.accounts.phone_numbers import normalize_ugandan_phone

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
    reply_to_message = serializers.SerializerMethodField()

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
            "offer_amount",
            "offer_status",
            "callback_name",
            "callback_phone",
            "image",
            "attachments",
            "reply_to",
            "reply_to_message",
            "is_read",
            "read_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "thread",
            "sender",
            "offer_status",
            "reply_to_message",
            "is_read",
            "read_at",
            "created_at",
        ]

    def get_reply_to_message(self, obj):
        replied_message = obj.reply_to

        if not replied_message:
            return None

        body = str(replied_message.body or "").strip()
        if not body:
            if replied_message.message_type == ChatMessage.TYPE_OFFER:
                body = f"Offer: UGX {replied_message.offer_amount:,.0f}"
            elif replied_message.message_type == ChatMessage.TYPE_CALLBACK:
                body = f"Callback request from {replied_message.callback_name}"
            else:
                first_attachment = replied_message.attachments.first()
                body = (
                    first_attachment.original_name
                    if first_attachment
                    else "Attachment"
                )

        return {
            "id": replied_message.id,
            "sender": replied_message.sender_id,
            "sender_name": replied_message.sender.full_name,
            "body": body[:180],
        }


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
    other_user_role = serializers.SerializerMethodField()
    other_user_is_admin = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    is_favourite = serializers.SerializerMethodField()
    is_archived = serializers.SerializerMethodField()
    is_spam = serializers.SerializerMethodField()
    is_marked_unread = serializers.SerializerMethodField()
    blocked_by_me = serializers.SerializerMethodField()

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
            "other_user_role",
            "other_user_is_admin",
            "last_message",
            "last_message_at",
            "buyer_unread_count",
            "seller_unread_count",
            "unread_count",
            "is_favourite",
            "is_archived",
            "is_spam",
            "is_marked_unread",
            "blocked_by_me",
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

    def get_other_user_role(self, obj):
        user = self._other_user(obj)
        return user.role if user else None

    def get_other_user_is_admin(self, obj):
        user = self._other_user(obj)
        return bool(user and user.role in {"admin", "moderator"})

    def get_is_favourite(self, obj):
        return self._state_value(obj, "user_is_favourite", "is_favourite")

    def get_is_archived(self, obj):
        return self._state_value(obj, "user_is_archived", "is_archived")

    def get_is_spam(self, obj):
        return self._state_value(obj, "user_is_spam", "is_spam")

    def get_is_marked_unread(self, obj):
        return self._state_value(obj, "user_marked_unread", "is_marked_unread")

    def get_blocked_by_me(self, obj):
        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return False

        if hasattr(obj, "user_blocked_other"):
            return bool(obj.user_blocked_other)

        other_user = self._other_user(obj)
        if not other_user:
            return False

        return ChatBlock.objects.filter(
            thread=obj,
            blocker=request.user,
            blocked_user=other_user,
            is_active=True,
        ).exists()


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
    reply_to = serializers.PrimaryKeyRelatedField(
        queryset=ChatMessage.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = ChatMessage
        fields = [
            "message_type",
            "body",
            "offer_amount",
            "callback_name",
            "callback_phone",
            "image",
            "reply_to",
        ]

    def validate(self, attrs):
        message_type = attrs.get("message_type", ChatMessage.TYPE_TEXT)
        body = attrs.get("body")
        image = attrs.get("image")
        offer_amount = attrs.get("offer_amount")
        reply_to = attrs.get("reply_to")
        callback_name = str(attrs.get("callback_name") or "").strip()
        callback_phone = str(attrs.get("callback_phone") or "").strip()

        if message_type == ChatMessage.TYPE_TEXT and not body:
            raise serializers.ValidationError(
                {"body": "Text message body is required."}
            )

        if message_type == ChatMessage.TYPE_IMAGE and not image:
            raise serializers.ValidationError(
                {"image": "Image is required for image messages."}
            )

        if message_type == ChatMessage.TYPE_OFFER:
            if offer_amount is None or offer_amount <= 0:
                raise serializers.ValidationError(
                    {"offer_amount": "Enter an offer amount greater than zero."}
                )

            thread = self.context.get("thread")
            request = self.context.get("request")
            if thread and offer_amount < (thread.listing.price * Decimal("0.50")):
                minimum_offer = thread.listing.price * Decimal("0.50")
                raise serializers.ValidationError(
                    {
                        "offer_amount": (
                            f"Offers cannot be below 50% of the ad price "
                            f"(UGX {minimum_offer:,.0f})."
                        )
                    }
                )
            if thread and request and request.user.id != thread.buyer_id:
                raise serializers.ValidationError(
                    {"message_type": "Only the buyer can make an offer."}
                )
        elif offer_amount is not None:
            raise serializers.ValidationError(
                {"offer_amount": "Offer amount is only valid for offer messages."}
            )

        if message_type == ChatMessage.TYPE_CALLBACK:
            thread = self.context.get("thread")
            request = self.context.get("request")
            if thread and request and request.user.id != thread.buyer_id:
                raise serializers.ValidationError(
                    {"message_type": "Only the buyer can request a callback."}
                )
            if len(callback_name) < 2:
                raise serializers.ValidationError(
                    {"callback_name": "Enter the name the seller should ask for."}
                )
            try:
                attrs["callback_phone"] = normalize_ugandan_phone(callback_phone)
            except ValueError as error:
                raise serializers.ValidationError(
                    {"callback_phone": str(error)}
                ) from error
            attrs["callback_name"] = callback_name
        elif callback_name or callback_phone:
            raise serializers.ValidationError(
                {"callback_phone": "Callback details are only valid for callback requests."}
            )

        thread = self.context.get("thread")
        if reply_to and thread and reply_to.thread_id != thread.id:
            raise serializers.ValidationError(
                {"reply_to": "The replied message is not in this conversation."}
            )

        return attrs

    def create(self, validated_data):
        if validated_data.get("message_type") == ChatMessage.TYPE_OFFER:
            validated_data["offer_status"] = ChatMessage.OFFER_PENDING

        return super().create(validated_data)


class ChatOfferActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(
        choices=["accept", "decline", "withdraw"],
    )



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
