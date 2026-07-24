from django.urls import path

from .consumers import ChatConsumer, PresenceConsumer


websocket_urlpatterns = [
    path(
        "ws/chats/presence/",
        PresenceConsumer.as_asgi(),
    ),
    path(
        "ws/chats/threads/<int:thread_id>/",
        ChatConsumer.as_asgi(),
    ),
]
