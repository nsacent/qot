from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from asgiref.sync import async_to_sync
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.core import signing
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.categories.models import Category
from apps.listings.models import Listing
from apps.locations.models import City, Region

from .models import (
    ChatMessage,
    ChatReport,
    ChatThread,
    ChatThreadParticipantState,
)
from .middleware import JWTAuthMiddlewareStack
from .routing import websocket_urlpatterns
from .socket_auth import (
    CHAT_SOCKET_TICKET_MAX_AGE_SECONDS,
    CHAT_SOCKET_TICKET_SALT,
    create_chat_socket_ticket,
)


class ChatDeliveryTests(APITestCase):
    def setUp(self):
        self.media_directory = TemporaryDirectory()
        self.media_override = override_settings(
            MEDIA_ROOT=Path(self.media_directory.name)
        )
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.addCleanup(self.media_directory.cleanup)

        self.buyer = User.objects.create_user(
            phone="+256700008001",
            email="chat-buyer@example.com",
            full_name="Chat Buyer",
            password="test-password",
            is_verified=True,
        )
        self.seller = User.objects.create_user(
            phone="+256700008002",
            email="chat-seller@example.com",
            full_name="Chat Seller",
            password="test-password",
            is_verified=True,
        )
        region = Region.objects.create(name="Chat Region", slug="chat-region")
        city = City.objects.create(
            region=region,
            name="Chat City",
            slug="chat-city",
        )
        category = Category.objects.create(
            name="Chat Category",
            slug="chat-category",
        )
        self.listing = Listing.objects.create(
            seller=self.seller,
            category=category,
            city=city,
            title="Chat test advert",
            slug="chat-test-advert",
            description="An advert used to test buyer and seller messages.",
            price="250000.00",
            status=Listing.STATUS_ACTIVE,
        )
        self.client.force_authenticate(self.buyer)

    @patch("apps.chats.views.broadcast_chat_message")
    @patch("apps.chats.views.create_message_notification")
    def test_thread_can_start_with_one_default_enquiry(
        self,
        notification_mock,
        broadcast_mock,
    ):
        payload = {
            "listing_id": self.listing.id,
            "initial_message": "Hi, is this ad still available?",
        }

        first_response = self.client.post(
            "/api/v1/chats/threads/",
            payload,
            format="json",
        )
        second_response = self.client.post(
            "/api/v1/chats/threads/",
            payload,
            format="json",
        )

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertEqual(ChatMessage.objects.count(), 1)
        self.assertEqual(
            first_response.data["initial_message"]["body"],
            payload["initial_message"],
        )
        self.assertIsNone(second_response.data["initial_message"])

        thread = ChatThread.objects.get()
        self.assertEqual(thread.last_message, payload["initial_message"])
        self.assertEqual(thread.seller_unread_count, 1)
        notification_mock.assert_called_once()
        broadcast_mock.assert_called_once()

    @patch("apps.chats.views.broadcast_chat_message")
    @patch("apps.chats.views.create_message_notification")
    def test_multiple_attachments_are_delivered_as_one_message(
        self,
        notification_mock,
        broadcast_mock,
    ):
        thread = ChatThread.objects.create(
            listing=self.listing,
            buyer=self.buyer,
            seller=self.seller,
        )
        files = [
            SimpleUploadedFile(
                "details.pdf",
                b"%PDF-1.4 test",
                content_type="application/pdf",
            ),
            SimpleUploadedFile(
                "notes.txt",
                b"Meet at the QOT office.",
                content_type="text/plain",
            ),
        ]

        response = self.client.post(
            f"/api/v1/chats/threads/{thread.id}/attachments/",
            {"message": "Here are the documents.", "files": files},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["chat_message"]["body"], "Here are the documents.")
        self.assertEqual(len(response.data["chat_message"]["attachments"]), 2)

        thread.refresh_from_db()
        message = ChatMessage.objects.get(thread=thread)
        self.assertEqual(message.attachments.count(), 2)
        self.assertEqual(thread.last_message, "Here are the documents.")
        self.assertEqual(thread.seller_unread_count, 1)
        notification_mock.assert_called_once_with(thread, message)
        broadcast_mock.assert_called_once()

    def test_unsupported_attachment_is_rejected(self):
        thread = ChatThread.objects.create(
            listing=self.listing,
            buyer=self.buyer,
            seller=self.seller,
        )

        response = self.client.post(
            f"/api/v1/chats/threads/{thread.id}/attachments/",
            {
                "files": [
                    SimpleUploadedFile(
                        "unsafe.exe",
                        b"not an executable",
                        content_type="application/octet-stream",
                    )
                ]
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ChatMessage.objects.count(), 0)

    def test_chat_folders_and_settings_are_private_to_each_participant(self):
        thread = ChatThread.objects.create(
            listing=self.listing,
            buyer=self.buyer,
            seller=self.seller,
        )

        favourite_response = self.client.patch(
            f"/api/v1/chats/threads/{thread.id}/state/",
            {"is_favourite": True},
            format="json",
        )
        favourite_list = self.client.get(
            "/api/v1/chats/threads/?filter=favourites"
        )

        self.assertEqual(favourite_response.status_code, status.HTTP_200_OK)
        self.assertTrue(favourite_response.data["thread"]["is_favourite"])
        self.assertEqual(favourite_list.data["tabs"]["favourites"], 1)
        self.assertEqual(favourite_list.data["results"][0]["id"], thread.id)

        archive_response = self.client.patch(
            f"/api/v1/chats/threads/{thread.id}/state/",
            {"is_archived": True},
            format="json",
        )
        all_list = self.client.get("/api/v1/chats/threads/?filter=all")
        archived_list = self.client.get(
            "/api/v1/chats/threads/?filter=archived"
        )

        self.assertEqual(archive_response.status_code, status.HTTP_200_OK)
        self.assertEqual(all_list.data["results"], [])
        self.assertEqual(archived_list.data["results"][0]["id"], thread.id)

        self.client.force_authenticate(self.seller)
        seller_list = self.client.get("/api/v1/chats/threads/?filter=all")

        self.assertEqual(seller_list.data["results"][0]["id"], thread.id)
        self.assertFalse(seller_list.data["results"][0]["is_favourite"])
        self.assertFalse(seller_list.data["results"][0]["is_archived"])

    def test_reporting_spam_moves_only_the_reporters_chat_to_spam(self):
        thread = ChatThread.objects.create(
            listing=self.listing,
            buyer=self.buyer,
            seller=self.seller,
        )

        response = self.client.patch(
            f"/api/v1/chats/threads/{thread.id}/state/",
            {"is_spam": True},
            format="json",
        )
        spam_list = self.client.get("/api/v1/chats/threads/?filter=spam")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["thread"]["is_spam"])
        self.assertFalse(response.data["thread"]["is_archived"])
        self.assertEqual(spam_list.data["results"][0]["id"], thread.id)
        self.assertTrue(
            ChatReport.objects.filter(
                thread=thread,
                reporter=self.buyer,
                reported_user=self.seller,
                reason=ChatReport.REASON_SPAM,
            ).exists()
        )

    def test_read_and_unread_folders_include_manually_marked_chats(self):
        thread = ChatThread.objects.create(
            listing=self.listing,
            buyer=self.buyer,
            seller=self.seller,
        )

        initial_read = self.client.get("/api/v1/chats/threads/?filter=read")
        self.assertEqual(initial_read.data["results"][0]["id"], thread.id)

        mark_unread = self.client.patch(
            f"/api/v1/chats/threads/{thread.id}/state/",
            {"is_marked_unread": True},
            format="json",
        )
        unread_list = self.client.get("/api/v1/chats/threads/?filter=unread")

        self.assertEqual(mark_unread.status_code, status.HTTP_200_OK)
        self.assertTrue(mark_unread.data["thread"]["is_marked_unread"])
        self.assertEqual(unread_list.data["results"][0]["id"], thread.id)

        mark_read = self.client.post(
            f"/api/v1/chats/threads/{thread.id}/mark-read/",
            {},
            format="json",
        )
        state = ChatThreadParticipantState.objects.get(
            thread=thread,
            user=self.buyer,
        )

        self.assertEqual(mark_read.status_code, status.HTTP_200_OK)
        self.assertFalse(state.is_marked_unread)

    def test_authenticated_verified_user_can_request_short_lived_socket_ticket(self):
        response = self.client.get("/api/v1/chats/socket-ticket/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["expires_in"],
            CHAT_SOCKET_TICKET_MAX_AGE_SECONDS,
        )
        payload = signing.loads(
            response.data["ticket"],
            salt=CHAT_SOCKET_TICKET_SALT,
            max_age=CHAT_SOCKET_TICKET_MAX_AGE_SECONDS,
        )
        self.assertEqual(payload["user_id"], self.buyer.id)

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "chat-realtime-tests",
            }
        },
        CHANNEL_LAYERS={
            "default": {
                "BACKEND": "channels.layers.InMemoryChannelLayer",
            }
        },
    )
    def test_thread_socket_broadcasts_presence_and_typing(self):
        thread = ChatThread.objects.create(
            listing=self.listing,
            buyer=self.buyer,
            seller=self.seller,
        )
        buyer_ticket = create_chat_socket_ticket(self.buyer)
        seller_ticket = create_chat_socket_ticket(self.seller)

        async def receive_event(communicator, event_type, user_id):
            for _ in range(8):
                event = await communicator.receive_json_from(timeout=1)
                if (
                    event.get("type") == event_type
                    and str(event.get("user_id")) == str(user_id)
                ):
                    return event

            self.fail(f"Did not receive {event_type} for user {user_id}.")

        async def exercise_socket():
            application = JWTAuthMiddlewareStack(URLRouter(websocket_urlpatterns))
            buyer_socket = WebsocketCommunicator(
                application,
                f"/ws/chats/threads/{thread.id}/?ticket={buyer_ticket}",
            )
            seller_socket = WebsocketCommunicator(
                application,
                f"/ws/chats/threads/{thread.id}/?ticket={seller_ticket}",
            )

            buyer_connected, _ = await buyer_socket.connect()
            seller_connected, _ = await seller_socket.connect()
            self.assertTrue(buyer_connected)
            self.assertTrue(seller_connected)

            presence_event = await receive_event(
                buyer_socket,
                "presence",
                self.seller.id,
            )
            self.assertTrue(presence_event["is_online"])

            await seller_socket.send_json_to(
                {"type": "typing", "is_typing": True}
            )
            typing_event = await receive_event(
                buyer_socket,
                "typing",
                self.seller.id,
            )
            self.assertTrue(typing_event["is_typing"])

            await seller_socket.disconnect()
            await buyer_socket.disconnect()

        async_to_sync(exercise_socket)()
