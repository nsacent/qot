from unittest.mock import patch

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.categories.models import Category
from apps.listings.models import Listing
from apps.locations.models import City, Region
from .models import Favorite


class FavoriteNotificationTests(APITestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(
            phone="+256700008001",
            email="buyer@example.com",
            full_name="Buyer",
            password="test-password",
            is_verified=True,
            phone_verified_at=timezone.now(),
        )
        self.seller = User.objects.create_user(
            phone="+256700008002",
            email="seller@example.com",
            full_name="Seller",
            password="test-password",
            is_verified=True,
            phone_verified_at=timezone.now(),
        )
        region = Region.objects.create(name="Favorite Region", slug="favorite-region")
        city = City.objects.create(region=region, name="Favorite City", slug="favorite-city")
        category = Category.objects.create(name="Favorite Category", slug="favorite-category")
        self.listing = Listing.objects.create(
            seller=self.seller,
            category=category,
            city=city,
            title="A valid favorite test ad",
            slug="favorite-test-ad",
            description="A sufficiently detailed description for the favorite test ad.",
            price="100000.00",
            status=Listing.STATUS_ACTIVE,
        )
        self.client.force_authenticate(self.buyer)

    @patch("apps.favorites.views.create_favorite_notification")
    def test_saving_an_ad_notifies_the_seller_once(self, notify_favorite):
        url = f"/api/v1/favorites/listings/{self.listing.id}/toggle/"

        first_response = self.client.post(url, {}, format="json")
        second_response = self.client.post(url, {}, format="json")

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        notify_favorite.assert_called_once()

    def test_saved_ads_only_returns_active_ads(self):
        Favorite.objects.create(user=self.buyer, listing=self.listing)

        active_response = self.client.get("/api/v1/favorites/")
        self.assertEqual(active_response.status_code, status.HTTP_200_OK)
        self.assertEqual(active_response.data["count"], 1)

        self.listing.status = Listing.STATUS_REJECTED
        self.listing.save(update_fields=["status"])

        rejected_response = self.client.get("/api/v1/favorites/")
        self.assertEqual(rejected_response.status_code, status.HTTP_200_OK)
        self.assertEqual(rejected_response.data["count"], 0)

    def test_rejected_own_ad_is_not_returned_in_saved_ads(self):
        self.listing.seller = self.buyer
        self.listing.status = Listing.STATUS_REJECTED
        self.listing.save(update_fields=["seller", "status"])
        Favorite.objects.create(user=self.buyer, listing=self.listing)

        response = self.client.get("/api/v1/favorites/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
