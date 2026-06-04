import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone
from apps.notifications.services import create_message_notification

from .models import ChatThread, ChatMessage


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.thread_id = self.scope["url_route"]["kwargs"]["thread_id"]
        self.room_group_name = f"chat_thread_{self.thread_id}"
        self.user = self.scope["user"]

        if not self.user.is_authenticated or self.user.is_banned:
            await self.close()
            return

        has_permission = await self.user_can_access_thread()

        if not has_permission:
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name,
            )

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        data = json.loads(text_data)
        body = data.get("body", "").strip()

        if not body:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "error",
                        "message": "Message body is required.",
                    }
                )
            )
            return

        message = await self.create_message(body)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": {
                    "id": message["id"],
                    "thread": message["thread_id"],
                    "sender": message["sender_id"],
                    "sender_name": message["sender_name"],
                    "message_type": message["message_type"],
                    "body": message["body"],
                    "created_at": message["created_at"],
                },
            },
        )

    async def chat_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "chat_message",
                    "message": event["message"],
                }
            )
        )

    @sync_to_async
    def user_can_access_thread(self):
        return ChatThread.objects.filter(
            id=self.thread_id,
            is_active=True,
        ).filter(
            buyer=self.user
        ).exists() or ChatThread.objects.filter(
            id=self.thread_id,
            is_active=True,
        ).filter(
            seller=self.user
        ).exists()

    @sync_to_async
    def create_message(self, body):
        thread = ChatThread.objects.select_related("buyer", "seller").get(
            id=self.thread_id,
            is_active=True,
        )

        message = ChatMessage.objects.create(
            thread=thread,
            sender=self.user,
            message_type=ChatMessage.TYPE_TEXT,
            body=body,
        )

        thread.last_message = body
        thread.last_message_at = message.created_at

        if self.user == thread.buyer:
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

        return {
            "id": message.id,
            "thread_id": thread.id,
            "sender_id": self.user.id,
            "sender_name": self.user.full_name,
            "message_type": message.message_type,
            "body": message.body,
            "created_at": message.created_at.isoformat(),
        }