from unittest.mock import patch

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.categories.models import Category
from apps.chats.models import ChatMessage, ChatThread
from apps.listings.models import Listing
from apps.locations.models import City, Region
from apps.notifications.models import Notification
from apps.notifications.services import create_transaction_review_prompts

from .models import SellerReview


class VerifiedTransactionReviewTests(APITestCase):
    def setUp(self):
        self.reviewer = User.objects.create_user(
            phone="+256700008001",
            email="reviewer@example.com",
            full_name="QOT Reviewer",
            password="test-password",
            is_verified=True,
            phone_verified_at=timezone.now(),
        )
        self.seller = User.objects.create_user(
            phone="+256700008002",
            email="reviewed-seller@example.com",
            full_name="Reviewed Seller",
            password="test-password",
            is_verified=True,
            phone_verified_at=timezone.now(),
        )
        self.outsider = User.objects.create_user(
            phone="+256700008003",
            email="review-outsider@example.com",
            full_name="Other Buyer",
            password="test-password",
            is_verified=True,
            phone_verified_at=timezone.now(),
        )
        region = Region.objects.create(name="Review Region", slug="review-region")
        city = City.objects.create(
            region=region,
            name="Review City",
            slug="review-city",
        )
        category = Category.objects.create(
            name="Review Category",
            slug="review-category",
        )
        self.listing = Listing.objects.create(
            seller=self.seller,
            category=category,
            city=city,
            title="Verified purchase advert",
            slug="verified-purchase-advert",
            description="An advert used to verify real transaction reviews.",
            price="250000.00",
            status=Listing.STATUS_SOLD,
            sold_at=timezone.now(),
        )
        self.thread = ChatThread.objects.create(
            listing=self.listing,
            buyer=self.reviewer,
            seller=self.seller,
        )
        self.offer = ChatMessage.objects.create(
            thread=self.thread,
            sender=self.reviewer,
            message_type=ChatMessage.TYPE_OFFER,
            offer_amount="220000.00",
            offer_status=ChatMessage.OFFER_ACCEPTED,
        )
        self.client.force_authenticate(self.reviewer)

    @patch("apps.notifications.services.broadcast_notification")
    def test_accepted_buyer_can_submit_verified_transaction_review(self, broadcast):
        response = self.client.post(
            "/api/v1/reviews/",
            {
                "seller": self.seller.id,
                "listing": self.listing.id,
                "rating": 5,
                "item_accuracy_rating": 5,
                "item_condition_rating": 4,
                "communication_rating": 5,
                "comment": "The item matched the ad and the seller communicated well.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        review = SellerReview.objects.get(reviewer=self.reviewer)
        self.assertTrue(review.is_verified_transaction)
        self.assertEqual(review.verified_offer, self.offer)
        self.assertEqual(review.item_condition_rating, 4)
        notification = Notification.objects.get(
            user=self.seller,
            notification_type=Notification.TYPE_REVIEW,
        )
        self.assertIn("verified 5-star review", notification.message)
        broadcast.assert_called_once_with(notification)

    def test_random_user_cannot_review_a_transaction(self):
        self.client.force_authenticate(self.outsider)

        response = self.client.post(
            "/api/v1/reviews/",
            {
                "seller": self.seller.id,
                "listing": self.listing.id,
                "rating": 5,
                "comment": "I should not be allowed to review this transaction.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("accepted", str(response.data).lower())
        self.assertFalse(SellerReview.objects.exists())

    def test_review_unlocks_only_after_ad_is_marked_sold(self):
        self.listing.status = Listing.STATUS_ACTIVE
        self.listing.sold_at = None
        self.listing.save(update_fields=["status", "sold_at"])

        response = self.client.post(
            "/api/v1/reviews/",
            {
                "seller": self.seller.id,
                "listing": self.listing.id,
                "rating": 4,
                "comment": "A valid review that must wait until completion.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("marks the ad as sold", str(response.data))

    def test_eligibility_and_pending_review_endpoints(self):
        eligibility = self.client.get(
            f"/api/v1/reviews/eligibility/?listing={self.listing.id}"
        )
        pending = self.client.get("/api/v1/reviews/eligible/")

        self.assertEqual(eligibility.status_code, status.HTTP_200_OK)
        self.assertTrue(eligibility.data["eligible"])
        self.assertEqual(
            eligibility.data["transaction"]["offer"],
            self.offer.id,
        )
        self.assertEqual(pending.status_code, status.HTTP_200_OK)
        self.assertEqual(pending.data["count"], 1)
        self.assertEqual(pending.data["results"][0]["listing"], self.listing.id)

    @patch("apps.listings.views.create_transaction_review_prompts")
    def test_marking_ad_sold_prompts_the_verified_buyer(self, prompt_mock):
        self.listing.status = Listing.STATUS_ACTIVE
        self.listing.sold_at = None
        self.listing.save(update_fields=["status", "sold_at"])
        self.client.force_authenticate(self.seller)

        response = self.client.post(
            f"/api/v1/listings/{self.listing.id}/mark-sold/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        prompt_mock.assert_called_once_with(self.listing)

    @patch("apps.notifications.services.broadcast_notification")
    def test_transaction_review_prompt_is_created_only_once(self, broadcast):
        first_result = create_transaction_review_prompts(self.listing)
        second_result = create_transaction_review_prompts(self.listing)

        self.assertEqual(len(first_result), 1)
        self.assertEqual(second_result, [])
        notification = Notification.objects.get(
            user=self.reviewer,
            title="Your purchase is ready to review",
        )
        self.assertEqual(notification.action_url, "/account/my-reviews")
        self.assertEqual(notification.listing, self.listing)
        broadcast.assert_called_once_with(notification)

    def test_legacy_unverified_review_is_not_public(self):
        SellerReview.objects.create(
            reviewer=self.reviewer,
            seller=self.seller,
            listing=self.listing,
            rating=5,
            comment="An old review without transaction proof.",
        )

        response = self.client.get(f"/api/v1/reviews/sellers/{self.seller.id}/")
        summary = self.client.get(
            f"/api/v1/reviews/sellers/{self.seller.id}/summary/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(summary.data["total_reviews"], 0)
