import json

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def _serialisable(value):
    return json.loads(json.dumps(value, default=str))


def broadcast_chat_message(thread, message_payload):
    channel_layer = get_channel_layer()

    if channel_layer is None:
        return

    async_to_sync(channel_layer.group_send)(
        f"chat_thread_{thread.id}",
        {
            "type": "chat_message",
            "message": _serialisable(message_payload),
        },
    )

    update = {
        "thread_id": thread.id,
        "last_message": thread.last_message or "",
        "last_message_at": (
            thread.last_message_at.isoformat() if thread.last_message_at else None
        ),
    }

    for user_id in {thread.buyer_id, thread.seller_id}:
        async_to_sync(channel_layer.group_send)(
            f"chat_user_{user_id}",
            {
                "type": "thread_updated",
                "thread": update,
            },
        )
