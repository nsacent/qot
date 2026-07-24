from django.db import transaction
from django.db.models import BooleanField, Count, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    ChatThread,
    ChatMessage,
    ChatMessageAttachment,
    ChatBlock,
    ChatReport,
    ChatThreadParticipantState,
)

from .permissions import IsThreadParticipant

from .serializers import (
    ChatThreadSerializer,
    ChatThreadCreateSerializer,
    ChatMessageSerializer,
    ChatMessageCreateSerializer,
    ChatAttachmentUploadSerializer,
    ChatBlockCreateSerializer,
    ChatBlockSerializer,
    ChatReportCreateSerializer,
    ChatReportSerializer,
    ChatThreadStateUpdateSerializer,
)

from apps.notifications.services import create_message_notification

from apps.common.permissions import IsNotBanned, IsVerifiedUser

from rest_framework.parsers import MultiPartParser, FormParser

from .realtime import broadcast_chat_message
from .socket_auth import create_chat_socket_ticket


CHAT_FOLDER_NAMES = {
    "all",
    "read",
    "unread",
    "favourites",
    "archived",
    "spam",
}


def chat_threads_for_user(user):
    participant_state = ChatThreadParticipantState.objects.filter(
        thread_id=OuterRef("pk"),
        user=user,
    )

    return (
        ChatThread.objects.filter(
            Q(buyer=user) | Q(seller=user),
            is_active=True,
        )
        .select_related(
            "listing",
            "listing__seller",
            "listing__category",
            "listing__city",
            "buyer",
            "buyer__profile",
            "seller",
            "seller__profile",
        )
        .prefetch_related("listing__images")
        .annotate(
            unread_count_value=Count(
                "messages",
                filter=(
                    Q(messages__is_read=False)
                    & ~Q(messages__sender=user)
                ),
            ),
            user_is_favourite=Coalesce(
                Subquery(participant_state.values("is_favourite")[:1]),
                Value(False),
                output_field=BooleanField(),
            ),
            user_is_archived=Coalesce(
                Subquery(participant_state.values("is_archived")[:1]),
                Value(False),
                output_field=BooleanField(),
            ),
            user_is_spam=Coalesce(
                Subquery(participant_state.values("is_spam")[:1]),
                Value(False),
                output_field=BooleanField(),
            ),
            user_marked_unread=Coalesce(
                Subquery(participant_state.values("is_marked_unread")[:1]),
                Value(False),
                output_field=BooleanField(),
            ),
        )
        .order_by("-last_message_at", "-created_at")
    )


def filter_chat_folder(queryset, folder):
    visible = queryset.filter(user_is_archived=False, user_is_spam=False)

    if folder == "unread":
        return visible.filter(
            Q(unread_count_value__gt=0) | Q(user_marked_unread=True)
        )

    if folder == "read":
        return visible.filter(
            unread_count_value=0,
            user_marked_unread=False,
        )

    if folder == "favourites":
        return queryset.filter(
            user_is_favourite=True,
            user_is_spam=False,
        )

    if folder == "archived":
        return queryset.filter(
            user_is_archived=True,
            user_is_spam=False,
        )

    if folder == "spam":
        return queryset.filter(user_is_spam=True)

    return visible


def get_other_chat_participant(thread, user):
    if thread.buyer_id == user.id:
        return thread.seller

    if thread.seller_id == user.id:
        return thread.buyer

    return None


def deliver_chat_message(thread, message, preview=None):
    thread.last_message = preview or message.body or "[Attachment]"
    thread.last_message_at = message.created_at

    if message.sender_id == thread.buyer_id:
        thread.seller_unread_count += 1
    else:
        thread.buyer_unread_count += 1

    thread.save(
        update_fields=[
            "last_message",
            "last_message_at",
            "buyer_unread_count",
            "seller_unread_count",
        ]
    )

    ChatThreadParticipantState.objects.filter(
        thread=thread,
        user=message.sender,
        is_marked_unread=True,
    ).update(is_marked_unread=False)

    create_message_notification(thread, message)


class ChatThreadListCreateAPIView(generics.ListCreateAPIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [
                permissions.IsAuthenticated(),
                IsNotBanned(),
                IsVerifiedUser(),
            ]

        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ChatThreadCreateSerializer

        return ChatThreadSerializer

    def get_queryset(self):
        folder = self.request.query_params.get("filter", "all").lower()

        if folder not in CHAT_FOLDER_NAMES:
            folder = "all"

        return filter_chat_folder(
            chat_threads_for_user(self.request.user),
            folder,
        )

    def list(self, request, *args, **kwargs):
        base_queryset = chat_threads_for_user(request.user)
        visible_queryset = base_queryset.filter(
            user_is_archived=False,
            user_is_spam=False,
        )
        tab_counts = {
            "all": visible_queryset.count(),
            "unread": visible_queryset.filter(
                Q(unread_count_value__gt=0) | Q(user_marked_unread=True)
            ).count(),
            "read": visible_queryset.filter(
                unread_count_value=0,
                user_marked_unread=False,
            ).count(),
            "favourites": base_queryset.filter(
                user_is_favourite=True,
                user_is_spam=False,
            ).count(),
            "archived": base_queryset.filter(
                user_is_archived=True,
                user_is_spam=False,
            ).count(),
            "spam": base_queryset.filter(user_is_spam=True).count(),
        }
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data["tabs"] = tab_counts
            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response({"results": serializer.data, "tabs": tab_counts})

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        listing = serializer.context["listing"]

        thread, created = ChatThread.objects.get_or_create(
            listing=listing,
            buyer=request.user,
            seller=listing.seller,
            defaults={
                "is_active": True,
            },
        )

        initial_message = serializer.validated_data.get("initial_message", "")
        created_message = None

        if created and initial_message:
            created_message = ChatMessage.objects.create(
                thread=thread,
                sender=request.user,
                body=initial_message,
                message_type=ChatMessage.TYPE_TEXT,
            )
            deliver_chat_message(thread, created_message)

        initial_message_data = (
            ChatMessageSerializer(
                created_message,
                context={"request": request},
            ).data
            if created_message
            else None
        )

        if created_message:
            broadcast_chat_message(thread, initial_message_data)

        return Response(
            {
                "message": "Chat thread created." if created else "Chat thread already exists.",
                "thread": ChatThreadSerializer(
                    thread,
                    context={"request": request},
                ).data,
                "initial_message": initial_message_data,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class ChatThreadDetailAPIView(generics.RetrieveAPIView):
    serializer_class = ChatThreadSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsThreadParticipant,
    ]

    def get_queryset(self):
        return chat_threads_for_user(self.request.user)


class ChatSocketTicketAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBanned,
        IsVerifiedUser,
    ]

    def get(self, request):
        return Response(
            {
                "ticket": create_chat_socket_ticket(request.user),
                "expires_in": 120,
            },
            status=status.HTTP_200_OK,
        )


class ChatThreadStateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def patch(self, request, thread_id):
        try:
            thread = (
                ChatThread.objects.filter(
                    Q(buyer=request.user) | Q(seller=request.user),
                    is_active=True,
                )
                .select_for_update()
                .get(pk=thread_id)
            )
        except ChatThread.DoesNotExist:
            return Response(
                {"detail": "Chat thread not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ChatThreadStateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        state, _ = ChatThreadParticipantState.objects.select_for_update().get_or_create(
            thread=thread,
            user=request.user,
        )

        updated_fields = []

        for field, value in serializer.validated_data.items():
            setattr(state, field, value)
            updated_fields.append(field)

        if serializer.validated_data.get("is_spam") is True:
            state.is_archived = False
            if "is_archived" not in updated_fields:
                updated_fields.append("is_archived")

            reported_user = get_other_chat_participant(thread, request.user)
            ChatReport.objects.get_or_create(
                thread=thread,
                reporter=request.user,
                reported_user=reported_user,
                reason=ChatReport.REASON_SPAM,
                is_resolved=False,
                defaults={
                    "description": "Conversation moved to spam by the participant.",
                },
            )

        state.save(update_fields=[*updated_fields, "updated_at"])
        refreshed_thread = chat_threads_for_user(request.user).get(pk=thread.pk)

        return Response(
            {
                "message": "Chat settings updated.",
                "thread": ChatThreadSerializer(
                    refreshed_thread,
                    context={"request": request},
                ).data,
            },
            status=status.HTTP_200_OK,
        )


class ChatMessageListCreateAPIView(generics.ListCreateAPIView):

    def get_permissions(self):
        if self.request.method == "POST":
            return [
                permissions.IsAuthenticated(),
                IsNotBanned(),
                IsVerifiedUser(),
            ]

        return [permissions.IsAuthenticated()]
    #permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ChatMessageCreateSerializer

        return ChatMessageSerializer

    def get_thread(self):
        return (
            ChatThread.objects
            .select_related("buyer", "seller", "listing")
            .get(
                pk=self.kwargs["thread_id"],
                is_active=True,
            )
        )
    
    def get_queryset(self):
        thread = self.get_thread()

        if self.request.user not in [thread.buyer, thread.seller]:
            return ChatMessage.objects.none()

        return (
            ChatMessage.objects
            .filter(thread=thread)
            .select_related("sender")
            .prefetch_related("attachments")
            .order_by("created_at")
        )

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        try:
            thread = self.get_thread()
        except ChatThread.DoesNotExist:
            return Response(
                {
                    "detail": "Chat thread not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if request.user not in [thread.buyer, thread.seller]:
            return Response(
                {
                    "detail": "You do not have permission to send messages in this thread."
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        
        other_user = get_other_chat_participant(thread, request.user)

        is_blocked = ChatBlock.objects.filter(
            blocker=other_user,
            blocked_user=request.user,
            thread=thread,
            is_active=True,
        ).exists()

        if is_blocked:
            return Response(
                {"detail": "You cannot send messages in this thread."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = serializer.save(
            thread=thread,
            sender=request.user,
        )

        deliver_chat_message(
            thread,
            message,
            preview=message.body or "[Image]",
        )

        message_data = ChatMessageSerializer(
            message,
            context={"request": request},
        ).data
        broadcast_chat_message(thread, message_data)

        return Response(
            message_data,
            status=status.HTTP_201_CREATED,
        )


class ChatMarkReadAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, thread_id):
        try:
            thread = ChatThread.objects.get(
                pk=thread_id,
                is_active=True,
            )
        except ChatThread.DoesNotExist:
            return Response(
                {
                    "detail": "Chat thread not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if request.user not in [thread.buyer, thread.seller]:
            return Response(
                {
                    "detail": "You do not have permission to access this thread."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        ChatMessage.objects.filter(
            thread=thread,
            is_read=False,
        ).exclude(
            sender=request.user,
        ).update(
            is_read=True,
            read_at=timezone.now(),
        )

        if request.user == thread.buyer:
            thread.buyer_unread_count = 0
            thread.save(update_fields=["buyer_unread_count"])
        else:
            thread.seller_unread_count = 0
            thread.save(update_fields=["seller_unread_count"])

        ChatThreadParticipantState.objects.filter(
            thread=thread,
            user=request.user,
            is_marked_unread=True,
        ).update(is_marked_unread=False)

        return Response(
            {
                "message": "Messages marked as read."
            },
            status=status.HTTP_200_OK,
        )
    
class ChatAttachmentUploadAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBanned,
        IsVerifiedUser,
    ]
    parser_classes = [MultiPartParser, FormParser]

    def get_file_type(self, file_name):
        file_name = file_name.lower()

        if file_name.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
            return ChatMessageAttachment.FILE_TYPE_IMAGE

        if file_name.endswith((
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".ppt",
            ".pptx",
            ".txt",
            ".csv",
        )):
            return ChatMessageAttachment.FILE_TYPE_DOCUMENT

        return ChatMessageAttachment.FILE_TYPE_OTHER

    @transaction.atomic
    def post(self, request, thread_id):
        try:
            thread = ChatThread.objects.get(
                id=thread_id,
                is_active=True,
            )
        except ChatThread.DoesNotExist:
            return Response(
                {"detail": "Chat thread not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if request.user not in [thread.buyer, thread.seller]:
            return Response(
                {"detail": "You are not allowed to send messages in this thread."},
                status=status.HTTP_403_FORBIDDEN,
            )

        other_user = get_other_chat_participant(thread, request.user)

        is_blocked = ChatBlock.objects.filter(
            blocker=other_user,
            blocked_user=request.user,
            thread=thread,
            is_active=True,
        ).exists()

        if is_blocked:
            return Response(
                {"detail": "You cannot send messages in this thread."},
                status=status.HTTP_403_FORBIDDEN,
            )

        uploaded_files = request.FILES.getlist("files") or request.FILES.getlist("file")

        if not uploaded_files:
            return Response(
                {"file": ["Choose at least one file to attach."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(uploaded_files) > 5:
            return Response(
                {"files": ["You can attach up to 5 files at a time."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        message_text = str(request.data.get("message", "")).strip()
        validated_files = []

        for uploaded_file in uploaded_files:
            serializer = ChatAttachmentUploadSerializer(
                data={
                    "message": message_text,
                    "file": uploaded_file,
                }
            )
            serializer.is_valid(raise_exception=True)
            validated_files.append(serializer.validated_data["file"])

        file_types = [self.get_file_type(file.name) for file in validated_files]
        message_type = (
            ChatMessage.TYPE_IMAGE
            if all(
                file_type == ChatMessageAttachment.FILE_TYPE_IMAGE
                for file_type in file_types
            )
            else ChatMessage.TYPE_TEXT
        )

        chat_message = ChatMessage.objects.create(
            thread=thread,
            sender=request.user,
            body=message_text,
            message_type=message_type,
)

        for uploaded_file, file_type in zip(validated_files, file_types):
            ChatMessageAttachment.objects.create(
                message=chat_message,
                file=uploaded_file,
                file_type=file_type,
                original_name=uploaded_file.name,
                size=uploaded_file.size,
            )

        attachment_label = (
            validated_files[0].name
            if len(validated_files) == 1
            else f"{len(validated_files)} attachments"
        )
        deliver_chat_message(
            thread,
            chat_message,
            preview=message_text or f"[Attachment] {attachment_label}",
        )

        message_data = ChatMessageSerializer(
            chat_message,
            context={"request": request},
        ).data
        broadcast_chat_message(thread, message_data)

        return Response(
            {
                "message": "Attachment sent successfully.",
                "chat_message": message_data,
            },
            status=status.HTTP_201_CREATED,
        )
    



class ChatBlockAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, thread_id):
        try:
            thread = ChatThread.objects.select_related(
                "buyer",
                "seller",
            ).get(
                id=thread_id,
                is_active=True,
            )
        except ChatThread.DoesNotExist:
            return Response(
                {"detail": "Chat thread not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        blocked_user = get_other_chat_participant(thread, request.user)

        if not blocked_user:
            return Response(
                {"detail": "You are not part of this chat thread."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ChatBlockCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        block, created = ChatBlock.objects.update_or_create(
            blocker=request.user,
            blocked_user=blocked_user,
            thread=thread,
            defaults={
                "reason": serializer.validated_data.get("reason", ""),
                "is_active": True,
            },
        )

        return Response(
            {
                "message": "User blocked successfully.",
                "block": ChatBlockSerializer(block).data,
            },
            status=status.HTTP_200_OK,
        )


class ChatUnblockAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, thread_id):
        try:
            thread = ChatThread.objects.select_related(
                "buyer",
                "seller",
            ).get(
                id=thread_id,
                is_active=True,
            )
        except ChatThread.DoesNotExist:
            return Response(
                {"detail": "Chat thread not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        blocked_user = get_other_chat_participant(thread, request.user)

        if not blocked_user:
            return Response(
                {"detail": "You are not part of this chat thread."},
                status=status.HTTP_403_FORBIDDEN,
            )

        block = ChatBlock.objects.filter(
            blocker=request.user,
            blocked_user=blocked_user,
            thread=thread,
            is_active=True,
        ).first()

        if not block:
            return Response(
                {"detail": "This user is not currently blocked."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        block.is_active = False
        block.save(update_fields=["is_active", "updated_at"])

        return Response(
            {
                "message": "User unblocked successfully.",
                "block": ChatBlockSerializer(block).data,
            },
            status=status.HTTP_200_OK,
        )


class ChatReportAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, thread_id):
        try:
            thread = ChatThread.objects.select_related(
                "buyer",
                "seller",
            ).get(
                id=thread_id,
                is_active=True,
            )
        except ChatThread.DoesNotExist:
            return Response(
                {"detail": "Chat thread not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        reported_user = get_other_chat_participant(thread, request.user)

        if not reported_user:
            return Response(
                {"detail": "You are not part of this chat thread."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ChatReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        report = ChatReport.objects.create(
            thread=thread,
            reporter=request.user,
            reported_user=reported_user,
            reason=serializer.validated_data["reason"],
            description=serializer.validated_data.get("description", ""),
        )

        if serializer.validated_data["reason"] == ChatReport.REASON_SPAM:
            ChatThreadParticipantState.objects.update_or_create(
                thread=thread,
                user=request.user,
                defaults={
                    "is_spam": True,
                    "is_archived": False,
                },
            )

        return Response(
            {
                "message": "Chat reported successfully.",
                "report": ChatReportSerializer(report).data,
            },
            status=status.HTTP_201_CREATED,
        )
