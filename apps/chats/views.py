from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ChatThread, ChatMessage
from .permissions import IsThreadParticipant
from .serializers import (
    ChatThreadSerializer,
    ChatThreadCreateSerializer,
    ChatMessageSerializer,
    ChatMessageCreateSerializer,
)

from apps.notifications.services import create_message_notification
from apps.common.permissions import IsNotBanned


class ChatThreadListCreateAPIView(generics.ListCreateAPIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated(), IsNotBanned()]

        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ChatThreadCreateSerializer

        return ChatThreadSerializer

    def get_queryset(self):
        return (
            ChatThread.objects
            .filter(
                Q(buyer=self.request.user) | Q(seller=self.request.user),
                is_active=True,
            )
            .select_related(
                "listing",
                "listing__seller",
                "listing__category",
                "listing__city",
                "buyer",
                "seller",
            )
            .prefetch_related("listing__images")
            .order_by("-last_message_at", "-created_at")
        )

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

        return Response(
            {
                "message": "Chat thread created." if created else "Chat thread already exists.",
                "thread": ChatThreadSerializer(
                    thread,
                    context={"request": request},
                ).data,
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
        return (
            ChatThread.objects
            .filter(
                Q(buyer=self.request.user) | Q(seller=self.request.user),
                is_active=True,
            )
            .select_related(
                "listing",
                "listing__seller",
                "listing__category",
                "listing__city",
                "buyer",
                "seller",
            )
            .prefetch_related("listing__images")
        )


class ChatMessageListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ChatMessageCreateSerializer

        return ChatMessageSerializer

    def get_thread(self):
        return ChatThread.objects.get(
            pk=self.kwargs["thread_id"],
            is_active=True,
        )

    def get_queryset(self):
        thread = self.get_thread()

        if self.request.user not in [thread.buyer, thread.seller]:
            return ChatMessage.objects.none()

        return (
            ChatMessage.objects
            .filter(thread=thread)
            .select_related("sender")
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

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = serializer.save(
            thread=thread,
            sender=request.user,
        )

        thread.last_message = message.body if message.body else "[Image]"
        thread.last_message_at = message.created_at

        if request.user == thread.buyer:
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

        create_message_notification(thread, message)

        return Response(
            ChatMessageSerializer(message, context={"request": request}).data,
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

        return Response(
            {
                "message": "Messages marked as read."
            },
            status=status.HTTP_200_OK,
        )