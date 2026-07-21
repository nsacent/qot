from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.categories.models import Category, CategoryFilter
from apps.listings.models import Listing, ListingAttribute
from apps.locations.models import City, Region


class AdminUserManagementTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            phone="+256700002001",
            email="admin-management@example.com",
            full_name="Admin Manager",
            password="test-password",
            role=User.ROLE_ADMIN,
            is_staff=True,
            is_verified=True,
        )
        self.moderator = User.objects.create_user(
            phone="+256700002002",
            email="moderator-management@example.com",
            full_name="Moderator Manager",
            password="test-password",
            role=User.ROLE_MODERATOR,
            is_staff=True,
            is_verified=True,
        )
        self.user = User.objects.create_user(
            phone="+256700002003",
            email="member-management@example.com",
            full_name="Marketplace Member",
            password="test-password",
        )
        self.superuser = User.objects.create_superuser(
            phone="+256700002004",
            email="superuser-management@example.com",
            full_name="Protected Superuser",
            password="test-password",
        )

    def detail_url(self, user):
        return f"/api/v1/admin-panel/users/{user.id}/"

    def test_admin_can_view_user_detail_and_statistics(self):
        self.client.force_authenticate(self.admin)

        response = self.client.get(self.detail_url(self.user))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.user.id)
        self.assertIn("stats", response.data)
        self.assertIn("listing_counts", response.data)
        self.assertTrue(response.data["permissions"]["can_edit"])
        self.assertTrue(response.data["permissions"]["can_manage_access"])

    def test_admin_can_edit_identity_role_and_verification(self):
        self.client.force_authenticate(self.admin)

        response = self.client.patch(
            self.detail_url(self.user),
            {
                "full_name": "Updated Member",
                "email": "updated-member@example.com",
                "role": User.ROLE_MODERATOR,
                "is_active": True,
                "is_verified": True,
            },
            format="json",
        )
        self.user.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.user.full_name, "Updated Member")
        self.assertEqual(self.user.email, "updated-member@example.com")
        self.assertEqual(self.user.role, User.ROLE_MODERATOR)
        self.assertTrue(self.user.is_staff)
        self.assertTrue(self.user.is_verified)

    def test_moderator_can_view_but_cannot_edit_accounts(self):
        self.client.force_authenticate(self.moderator)

        get_response = self.client.get(self.detail_url(self.user))
        patch_response = self.client.patch(
            self.detail_url(self.user),
            {"full_name": "Not Allowed"},
            format="json",
        )

        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        self.assertFalse(get_response.data["permissions"]["can_edit"])
        self.assertEqual(patch_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_moderator_cannot_ban_staff_but_can_ban_normal_user(self):
        self.client.force_authenticate(self.moderator)

        staff_response = self.client.post(
            f"/api/v1/admin-panel/users/{self.admin.id}/ban/",
            {"banned_reason": "Not permitted"},
            format="json",
        )
        user_response = self.client.post(
            f"/api/v1/admin-panel/users/{self.user.id}/ban/",
            {"banned_reason": "Repeated marketplace abuse"},
            format="json",
        )
        self.user.refresh_from_db()

        self.assertEqual(staff_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(user_response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.user.is_banned)
        self.assertEqual(self.user.banned_reason, "Repeated marketplace abuse")

    def test_admin_cannot_deactivate_own_account(self):
        self.client.force_authenticate(self.admin)

        response = self.client.patch(
            self.detail_url(self.admin),
            {"is_active": False},
            format="json",
        )
        self.admin.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(self.admin.is_active)

    def test_account_must_retain_a_login_identifier(self):
        self.client.force_authenticate(self.admin)

        response = self.client.patch(
            self.detail_url(self.user),
            {"phone": "", "email": ""},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_regular_admin_cannot_edit_or_ban_a_superuser(self):
        self.client.force_authenticate(self.admin)

        detail_response = self.client.get(self.detail_url(self.superuser))
        patch_response = self.client.patch(
            self.detail_url(self.superuser),
            {"full_name": "Not Allowed"},
            format="json",
        )
        ban_response = self.client.post(
            f"/api/v1/admin-panel/users/{self.superuser.id}/ban/",
            {"banned_reason": "Not allowed"},
            format="json",
        )

        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertFalse(detail_response.data["permissions"]["can_edit"])
        self.assertFalse(detail_response.data["permissions"]["can_manage_access"])
        self.assertEqual(patch_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(ban_response.status_code, status.HTTP_403_FORBIDDEN)


class AdminListingManagementTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            phone="+256700003001",
            email="listing-admin@example.com",
            full_name="Listing Admin",
            password="test-password",
            role=User.ROLE_ADMIN,
            is_staff=True,
        )
        self.seller = User.objects.create_user(
            phone="+256700003002",
            email="listing-seller@example.com",
            full_name="Listing Seller",
            password="test-password",
            is_verified=True,
        )
        self.region = Region.objects.create(name="Central Test", slug="central-test")
        self.city = City.objects.create(
            region=self.region,
            name="Kampala Test",
            slug="kampala-test",
        )
        self.category = Category.objects.create(
            name="Test Vehicles",
            slug="test-vehicles",
        )
        self.listing = Listing.objects.create(
            seller=self.seller,
            category=self.category,
            city=self.city,
            title="Test marketplace listing",
            slug="test-marketplace-listing",
            description="A listing used to verify the admin moderation workspace.",
            price="15000000.00",
            currency="UGX",
            condition=Listing.CONDITION_USED,
            status=Listing.STATUS_PENDING,
        )
        self.client.force_authenticate(self.admin)

    def detail_url(self):
        return f"/api/v1/admin-panel/listings/{self.listing.id}/"

    def test_admin_can_view_complete_listing_detail(self):
        response = self.client.get(self.detail_url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.listing.id)
        self.assertEqual(response.data["seller_email"], self.seller.email)
        self.assertEqual(response.data["region_name"], self.region.name)
        self.assertIn("images", response.data)
        self.assertIn("attributes", response.data)
        self.assertIn("open_reports_count", response.data)

    def test_only_active_listing_can_be_featured(self):
        response = self.client.post(
            f"/api/v1/admin-panel/listings/{self.listing.id}/feature/",
            {"days": 7},
            format="json",
        )
        self.listing.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(self.listing.is_featured)

    def test_rejecting_listing_removes_featured_status(self):
        self.listing.status = Listing.STATUS_ACTIVE
        self.listing.is_featured = True
        self.listing.featured_until = timezone.now() + timedelta(days=7)
        self.listing.save()

        response = self.client.post(
            f"/api/v1/admin-panel/listings/{self.listing.id}/reject/",
            {"rejection_reason": "The listing needs clearer ownership details."},
            format="json",
        )
        self.listing.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.listing.status, Listing.STATUS_REJECTED)
        self.assertFalse(self.listing.is_featured)
        self.assertIsNone(self.listing.featured_until)

    def test_delete_action_soft_deletes_listing(self):
        self.listing.status = Listing.STATUS_ACTIVE
        self.listing.is_featured = True
        self.listing.featured_until = timezone.now() + timedelta(days=7)
        self.listing.save()

        response = self.client.post(
            f"/api/v1/admin-panel/listings/{self.listing.id}/delete/"
        )
        self.listing.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.listing.status, Listing.STATUS_DELETED)
        self.assertFalse(self.listing.is_featured)
        self.assertIsNone(self.listing.featured_until)
        self.assertEqual(response.data["listing"]["status"], Listing.STATUS_DELETED)

    def test_admin_can_edit_listing_content_without_changing_status(self):
        self.listing.status = Listing.STATUS_ACTIVE
        self.listing.is_featured = True
        self.listing.featured_until = timezone.now() + timedelta(days=7)
        self.listing.save()
        category_filter = CategoryFilter.objects.create(
            category=self.category,
            name="Mileage",
            key="mileage",
            filter_type=CategoryFilter.TYPE_NUMBER,
        )

        response = self.client.patch(
            self.detail_url(),
            {
                "title": "Admin corrected marketplace listing",
                "price": "14500000.00",
                "attributes": [
                    {
                        "category_filter_id": category_filter.id,
                        "value_number": "85000",
                    }
                ],
            },
            format="json",
        )
        self.listing.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.listing.title, "Admin corrected marketplace listing")
        self.assertEqual(str(self.listing.price), "14500000.00")
        self.assertEqual(self.listing.status, Listing.STATUS_ACTIVE)
        self.assertTrue(self.listing.is_featured)
        self.assertIsNotNone(self.listing.featured_until)
        self.assertTrue(
            ListingAttribute.objects.filter(
                listing=self.listing,
                category_filter=category_filter,
                value_number=85000,
            ).exists()
        )
        self.assertEqual(response.data["title"], self.listing.title)

    def test_normal_user_cannot_edit_another_sellers_listing_as_admin(self):
        other_user = User.objects.create_user(
            phone="+256700003003",
            email="other-listing-user@example.com",
            full_name="Other Listing User",
            password="test-password",
        )
        self.client.force_authenticate(other_user)

        response = self.client.patch(
            self.detail_url(),
            {"title": "Unauthorized edit"},
            format="json",
        )
        self.listing.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertNotEqual(self.listing.title, "Unauthorized edit")

    def test_deleted_listing_cannot_be_edited(self):
        self.listing.status = Listing.STATUS_DELETED
        self.listing.save(update_fields=["status", "updated_at"])

        response = self.client.patch(
            self.detail_url(),
            {"title": "Edited after deletion"},
            format="json",
        )
        self.listing.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Deleted listings cannot be edited.")
        self.assertNotEqual(self.listing.title, "Edited after deletion")
