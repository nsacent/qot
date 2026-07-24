from django.urls import path

from .views import (
    ChatThreadListCreateAPIView,
    ChatThreadDetailAPIView,
    ChatMessageListCreateAPIView,
    ChatMarkReadAPIView,
    ChatAttachmentUploadAPIView,
    ChatAttachmentDownloadAPIView,
    ChatBlockAPIView,
    ChatUnblockAPIView,
    ChatReportAPIView,
    ChatSocketTicketAPIView,
    ChatThreadStateAPIView,
)


app_name = "chats"


urlpatterns = [
    path("socket-ticket/", ChatSocketTicketAPIView.as_view(), name="socket_ticket"),
    path("threads/", ChatThreadListCreateAPIView.as_view(), name="thread_list_create"),
    path("threads/<int:pk>/", ChatThreadDetailAPIView.as_view(), name="thread_detail"),
    path(
        "threads/<int:thread_id>/state/",
        ChatThreadStateAPIView.as_view(),
        name="thread_state",
    ),
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
    path(
        "attachments/<int:pk>/",
        ChatAttachmentDownloadAPIView.as_view(),
        name="chat_attachment_download",
    ),
    path("threads/<int:thread_id>/block/", ChatBlockAPIView.as_view(), name="chat_block"),
    path("threads/<int:thread_id>/unblock/", ChatUnblockAPIView.as_view(), name="chat_unblock"),
    path("threads/<int:thread_id>/report/", ChatReportAPIView.as_view(), name="chat_report"),
]
