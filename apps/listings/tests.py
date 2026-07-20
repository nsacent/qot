from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.categories.models import Category
from apps.locations.models import City, Region

from .models import Listing, ListingImage, PendingListingImage


class ListingLifecycleTests(APITestCase):
    def setUp(self):
        self.media_directory = TemporaryDirectory()
        self.media_override = override_settings(
            MEDIA_ROOT=Path(self.media_directory.name)
        )
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.addCleanup(self.media_directory.cleanup)

        self.owner = User.objects.create_user(
            phone="+256700001001",
            email="listing-owner@example.com",
            full_name="Listing Owner",
            password="test-password",
            is_verified=True,
        )
        self.other_user = User.objects.create_user(
            phone="+256700001002",
            email="listing-buyer@example.com",
            full_name="Listing Buyer",
            password="test-password",
            is_verified=True,
        )
        self.region = Region.objects.create(name="Test Region", slug="test-region")
        self.city = City.objects.create(
            region=self.region,
            name="Test City",
            slug="test-city",
        )
        self.category = Category.objects.create(
            name="Test Category",
            slug="test-category",
        )

    def create_listing(self, status_value=Listing.STATUS_ACTIVE, **overrides):
        values = {
            "seller": self.owner,
            "category": self.category,
            "city": self.city,
            "title": f"Test listing {Listing.objects.count() + 1}",
            "slug": f"test-listing-{Listing.objects.count() + 1}",
            "description": "A listing used by the API test suite.",
            "price": "100000.00",
            "condition": Listing.CONDITION_USED,
            "status": status_value,
            "expires_at": timezone.now() + timedelta(days=30),
        }
        values.update(overrides)
        return Listing.objects.create(**values)

    def authenticate_owner(self):
        self.client.force_authenticate(self.owner)

    def test_mine_filter_requires_authentication(self):
        self.create_listing()

        response = self.client.get("/api/v1/listings/?mine=true")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_pending_listing_is_private_but_visible_to_owner(self):
        listing = self.create_listing(Listing.STATUS_PENDING)

        anonymous_response = self.client.get(f"/api/v1/listings/{listing.id}/")
        self.assertEqual(anonymous_response.status_code, status.HTTP_404_NOT_FOUND)

        self.authenticate_owner()
        owner_response = self.client.get(f"/api/v1/listings/{listing.id}/")
        listing.refresh_from_db()

        self.assertEqual(owner_response.status_code, status.HTTP_200_OK)
        self.assertEqual(listing.views_count, 0)

    def test_active_listing_view_count_uses_public_detail(self):
        listing = self.create_listing()

        response = self.client.get(f"/api/v1/listings/{listing.id}/")
        listing.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(listing.views_count, 1)

    def test_pending_listing_cannot_bypass_moderation(self):
        listing = self.create_listing(Listing.STATUS_PENDING)
        self.authenticate_owner()

        for action in ("mark-sold", "mark-available", "relist", "renew"):
            response = self.client.post(
                f"/api/v1/listings/{listing.id}/{action}/",
                {},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        listing.refresh_from_db()
        self.assertEqual(listing.status, Listing.STATUS_PENDING)

    def test_valid_listing_transitions_still_work(self):
        unavailable = self.create_listing(Listing.STATUS_UNAVAILABLE)
        expired = self.create_listing(Listing.STATUS_EXPIRED)
        active = self.create_listing(Listing.STATUS_ACTIVE)
        self.authenticate_owner()

        available_response = self.client.post(
            f"/api/v1/listings/{unavailable.id}/mark-available/",
            {},
            format="json",
        )
        relist_response = self.client.post(
            f"/api/v1/listings/{expired.id}/relist/",
            {},
            format="json",
        )
        renew_response = self.client.post(
            f"/api/v1/listings/{active.id}/renew/",
            {},
            format="json",
        )

        self.assertEqual(available_response.status_code, status.HTTP_200_OK)
        self.assertEqual(relist_response.status_code, status.HTTP_200_OK)
        self.assertEqual(renew_response.status_code, status.HTTP_200_OK)

    def test_seller_delete_is_soft_delete(self):
        listing = self.create_listing()
        self.authenticate_owner()

        response = self.client.delete(
            f"/api/v1/seller/listings/{listing.id}/"
        )
        listing.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(listing.status, Listing.STATUS_DELETED)

    def test_refurbished_condition_is_rejected(self):
        self.authenticate_owner()

        response = self.client.post(
            "/api/v1/listings/",
            {
                "category": self.category.id,
                "city": self.city.id,
                "title": "Unsupported condition",
                "description": "This should not pass model choice validation.",
                "price": "1000.00",
                "condition": "refurbished",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("condition", response.data)

    def test_feature_expiry_command_only_clears_promotion(self):
        listing = self.create_listing(
            is_featured=True,
            featured_until=timezone.now() - timedelta(minutes=1),
        )

        call_command("expire_featured_listings")
        listing.refresh_from_db()

        self.assertFalse(listing.is_featured)
        self.assertIsNone(listing.featured_until)
        self.assertEqual(listing.status, Listing.STATUS_ACTIVE)

    def test_featured_sort_returns_only_current_featured_listings(self):
        current_featured = self.create_listing(
            is_featured=True,
            featured_until=timezone.now() + timedelta(days=2),
        )
        indefinite_featured = self.create_listing(
            is_featured=True,
            featured_until=None,
        )
        self.create_listing(
            is_featured=True,
            featured_until=timezone.now() - timedelta(minutes=1),
        )
        self.create_listing(is_featured=False)

        response = self.client.get("/api/v1/listings/?sort=featured")
        listing_ids = [item["id"] for item in response.data["results"]]

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(listing_ids),
            {current_featured.id, indefinite_featured.id},
        )

    def test_missing_image_cleanup_repairs_primary_image(self):
        listing = self.create_listing()
        existing_image = ListingImage.objects.create(
            listing=listing,
            image=SimpleUploadedFile(
                "existing.jpg",
                b"existing-image-content",
                content_type="image/jpeg",
            ),
            is_primary=False,
        )
        missing_image = ListingImage.objects.create(
            listing=listing,
            image="listings/images/missing.jpg",
            is_primary=True,
        )

        call_command("cleanup_missing_listing_images", delete_missing=True)

        self.assertFalse(ListingImage.objects.filter(pk=missing_image.pk).exists())
        existing_image.refresh_from_db()
        self.assertTrue(existing_image.is_primary)

    def test_cleanup_pending_images_removes_database_row_and_file(self):
        pending_image = PendingListingImage.objects.create(
            user=self.owner,
            image=SimpleUploadedFile("abandoned.jpg", b"abandoned-image"),
        )
        PendingListingImage.objects.filter(pk=pending_image.pk).update(
            created_at=timezone.now() - timedelta(days=2)
        )
        image_path = Path(pending_image.image.path)

        call_command("cleanup_pending_images")

        self.assertFalse(PendingListingImage.objects.filter(pk=pending_image.pk).exists())
        self.assertFalse(image_path.exists())
