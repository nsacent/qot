import json
from time import monotonic

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.notifications.services import create_message_notification

from .models import ChatBlock, ChatMessage, ChatThread
from .presence import connect_user, disconnect_user, refresh_user


PRESENCE_GROUP = "chat_presence"
LAST_SEEN_WRITE_INTERVAL_SECONDS = 60


def update_user_last_seen(user_id):
    last_seen_at = timezone.now()
    get_user_model().objects.filter(pk=user_id).update(
        last_seen_at=last_seen_at,
    )
    return last_seen_at.isoformat()


class ChatPresenceMixin:
    async def start_presence(self):
        self.presence_group_name = PRESENCE_GROUP
        self.user_group_name = f"chat_user_{self.user.id}"

        await self.channel_layer.group_add(
            self.presence_group_name,
            self.channel_name,
        )
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name,
        )

        last_seen_at = await self.persist_last_seen(force=True)

        connections = await sync_to_async(
            connect_user,
            thread_sensitive=False,
        )(self.user.id)

        if connections == 1:
            await self.broadcast_presence(True, last_seen_at)

    async def stop_presence(self):
        if not getattr(self, "user", None) or not self.user.is_authenticated:
            return

        last_seen_at = await self.persist_last_seen(force=True)
        connections = await sync_to_async(
            disconnect_user,
            thread_sensitive=False,
        )(self.user.id)

        if connections == 0:
            await self.broadcast_presence(False, last_seen_at)

        if hasattr(self, "user_group_name"):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name,
            )

        if hasattr(self, "presence_group_name"):
            await self.channel_layer.group_discard(
                self.presence_group_name,
                self.channel_name,
            )

    async def persist_last_seen(self, force=False):
        last_write = getattr(self, "last_seen_write_at", 0)

        if (
            not force
            and monotonic() - last_write < LAST_SEEN_WRITE_INTERVAL_SECONDS
        ):
            return None

        self.last_seen_write_at = monotonic()
        return await sync_to_async(
            update_user_last_seen,
            thread_sensitive=False,
        )(self.user.id)

    async def broadcast_presence(self, is_online, last_seen_at=None):
        await self.channel_layer.group_send(
            PRESENCE_GROUP,
            {
                "type": "presence_status",
                "user_id": self.user.id,
                "is_online": is_online,
                "last_seen_at": last_seen_at,
            },
        )

    async def refresh_presence(self):
        await sync_to_async(
            refresh_user,
            thread_sensitive=False,
        )(self.user.id)
        await self.persist_last_seen()

    async def presence_status(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "presence",
                    "user_id": event["user_id"],
                    "is_online": event["is_online"],
                    "last_seen_at": event.get("last_seen_at"),
                }
            )
        )

    async def thread_updated(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "thread_updated",
                    "thread": event["thread"],
                }
            )
        )


class PresenceConsumer(ChatPresenceMixin, AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]

        if (
            not self.user.is_authenticated
            or self.user.is_banned
            or not self.user.is_verified
        ):
            await self.close()
            return

        await self.accept()
        await self.start_presence()

    async def disconnect(self, close_code):
        await self.stop_presence()

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        if data.get("type") == "heartbeat":
            await self.refresh_presence()


class ChatConsumer(ChatPresenceMixin, AsyncWebsocketConsumer):
    async def connect(self):
        self.thread_id = self.scope["url_route"]["kwargs"]["thread_id"]
        self.room_group_name = f"chat_thread_{self.thread_id}"
        self.user = self.scope["user"]

        if (
            not self.user.is_authenticated
            or self.user.is_banned
            or not self.user.is_verified
        ):
            await self.close()
            return

        if not await self.user_can_access_thread():
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )
        await self.accept()
        await self.start_presence()

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            if getattr(self, "user", None) and self.user.is_authenticated:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "typing_status",
                        "user_id": self.user.id,
                        "user_name": self.user.full_name,
                        "is_typing": False,
                    },
                )

            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name,
            )

        await self.stop_presence()

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send_error("Invalid chat event.")
            return

        event_type = data.get("type") or "chat_message"

        if event_type == "heartbeat":
            await self.refresh_presence()
            return

        if event_type == "typing":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "typing_status",
                    "user_id": self.user.id,
                    "user_name": self.user.full_name,
                    "is_typing": bool(data.get("is_typing")),
                },
            )
            return

        body = str(data.get("body", "")).strip()

        if not body:
            await self.send_error("Message body is required.")
            return

        if len(body) > 1000:
            await self.send_error("Message body cannot exceed 1000 characters.")
            return

        try:
            message = await self.create_message(body)
        except PermissionError:
            await self.send_error("You cannot send messages in this thread.")
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message,
            },
        )

        thread_update = {
            "thread_id": int(self.thread_id),
            "last_message": message["body"],
            "last_message_at": message["created_at"],
        }
        thread_users = await self.get_thread_user_ids()

        for user_id in thread_users:
            await self.channel_layer.group_send(
                f"chat_user_{user_id}",
                {
                    "type": "thread_updated",
                    "thread": thread_update,
                },
            )

    async def send_error(self, message):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "error",
                    "message": message,
                }
            )
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

    async def typing_status(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "typing",
                    "user_id": event["user_id"],
                    "user_name": event["user_name"],
                    "is_typing": event["is_typing"],
                }
            )
        )

    @sync_to_async
    def user_can_access_thread(self):
        return (
            ChatThread.objects.filter(
                id=self.thread_id,
                is_active=True,
            )
            .filter(buyer=self.user)
            .exists()
            or ChatThread.objects.filter(
                id=self.thread_id,
                is_active=True,
            )
            .filter(seller=self.user)
            .exists()
        )

    @sync_to_async
    def get_thread_user_ids(self):
        thread = ChatThread.objects.only("buyer_id", "seller_id").get(
            id=self.thread_id,
        )
        return [thread.buyer_id, thread.seller_id]

    @sync_to_async
    def create_message(self, body):
        thread = ChatThread.objects.select_related("buyer", "seller").get(
            id=self.thread_id,
            is_active=True,
        )
        other_user = thread.seller if self.user == thread.buyer else thread.buyer

        if ChatBlock.objects.filter(
            blocker=other_user,
            blocked_user=self.user,
            thread=thread,
            is_active=True,
        ).exists():
            raise PermissionError

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
            "thread": thread.id,
            "sender": self.user.id,
            "sender_name": self.user.full_name,
            "message_type": message.message_type,
            "body": message.body,
            "attachments": [],
            "is_read": False,
            "read_at": None,
            "created_at": message.created_at.isoformat(),
        }
