from django.urls import path

from .views import (
    ChatThreadListCreateAPIView,
    ChatThreadDetailAPIView,
    ChatMessageListCreateAPIView,
    ChatMarkReadAPIView,
    ChatAttachmentUploadAPIView,
)


app_name = "chats"


urlpatterns = [
    path("threads/", ChatThreadListCreateAPIView.as_view(), name="thread_list_create"),
    path("threads/<int:pk>/", ChatThreadDetailAPIView.as_view(), name="thread_detail"),
    path(
        "threads/<int:thread_id>/messages/",
        ChatMessageListCreateAPIView.as_view(),
        name="message_list_create",
    ),
    path(
        "threads/<int:thread_id>/mark-read/",
        ChatMarkReadAPIView.as_view(),
        name="mark_read",
    ),
    path(
        "threads/<int:thread_id>/attachments/",
        ChatAttachmentUploadAPIView.as_view(),
        name="chat_attachment_upload",
    ),
]