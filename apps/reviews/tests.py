from unittest.mock import patch

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.notifications.models import Notification


class SellerReviewNotificationTests(APITestCase):
    def setUp(self):
        self.reviewer = User.objects.create_user(
            phone="+256700008001",
            email="reviewer@example.com",
            full_name="QOT Reviewer",
            password="test-password",
            phone_verified_at=timezone.now(),
        )
        self.seller = User.objects.create_user(
            phone="+256700008002",
            email="reviewed-seller@example.com",
            full_name="Reviewed Seller",
            password="test-password",
        )
        self.client.force_authenticate(self.reviewer)

    @patch("apps.notifications.services.broadcast_notification")
    def test_new_review_notifies_seller(self, broadcast):
        response = self.client.post(
            "/api/v1/reviews/",
            {
                "seller": self.seller.id,
                "rating": 5,
                "comment": "Excellent seller.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        notification = Notification.objects.get(
            user=self.seller,
            notification_type=Notification.TYPE_REVIEW,
        )
        self.assertIn("5-star review", notification.message)
        broadcast.assert_called_once_with(notification)
