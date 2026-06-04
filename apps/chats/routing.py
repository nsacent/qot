from django.urls import path

from .consumers import ChatConsumer


websocket_urlpatterns = [
    path(
        "ws/chats/threads/<int:thread_id>/",
        ChatConsumer.as_asgi(),
    ),
]