from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.categories.models import Category
from apps.listings.models import Listing
from apps.locations.models import City, Region

from .models import ChatMessage, ChatThread


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

    @patch("apps.chats.views.create_message_notification")
    def test_thread_can_start_with_one_default_enquiry(self, notification_mock):
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

    @patch("apps.chats.views.create_message_notification")
    def test_multiple_attachments_are_delivered_as_one_message(self, notification_mock):
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
