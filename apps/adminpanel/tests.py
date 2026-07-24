from datetime import timedelta
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.categories.models import Category, CategoryFilter
from apps.listings.models import Listing, ListingAttribute
from apps.locations.models import City, Region
from apps.adminpanel.backups import create_backup, list_backups, restore_backup
from apps.adminpanel.models import AdminActivityLog


class BackupServiceRoundTripTests(SimpleTestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.database_path = self.root / "source.sqlite3"
        self.backup_root = self.root / "backups"
        self.settings_override = override_settings(
            DATABASES={
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": self.database_path,
                }
            },
            ADMIN_BACKUP_ROOT=self.backup_root,
        )
        self.settings_override.enable()

        with sqlite3.connect(self.database_path) as connection:
            connection.execute("CREATE TABLE sample (value TEXT NOT NULL)")
            connection.execute("INSERT INTO sample (value) VALUES ('before')")

    def tearDown(self):
        self.settings_override.disable()
        self.temporary_directory.cleanup()

    def read_value(self):
        with sqlite3.connect(self.database_path) as connection:
            return connection.execute("SELECT value FROM sample").fetchone()[0]

    def test_create_list_and_restore_round_trip(self):
        backup = create_backup(created_by={"id": 1}, kind="manual")

        with sqlite3.connect(self.database_path) as connection:
            connection.execute("UPDATE sample SET value = 'after'")

        result = restore_backup(backup["name"], restored_by={"id": 1})

        self.assertEqual(self.read_value(), "before")
        self.assertEqual(result["backup"]["name"], backup["name"])
        self.assertEqual(result["safety_backup"]["kind"], "pre_restore_safety")
        self.assertEqual(len(list_backups()), 2)


class AdminBackupManagementTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            phone="+256700001001",
            email="backup-admin@example.com",
            full_name="Backup Admin",
            password="test-password",
            role=User.ROLE_ADMIN,
            is_staff=True,
        )
        self.moderator = User.objects.create_user(
            phone="+256700001002",
            email="backup-moderator@example.com",
            full_name="Backup Moderator",
            password="test-password",
            role=User.ROLE_MODERATOR,
            is_staff=True,
        )

    @patch("apps.adminpanel.views.list_backups")
    def test_admin_can_list_backups(self, list_backups_mock):
        list_backups_mock.return_value = [{"name": "qot-db-20260723-120000-acde1234.dump"}]
        self.client.force_authenticate(self.admin)

        response = self.client.get("/api/v1/admin-panel/backups/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    @patch("apps.adminpanel.views.create_backup")
    def test_admin_can_create_backup(self, create_backup_mock):
        create_backup_mock.return_value = {
            "name": "qot-db-20260723-120000-acde1234.dump",
            "size_bytes": 1024,
        }
        self.client.force_authenticate(self.admin)

        response = self.client.post("/api/v1/admin-panel/backups/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        create_backup_mock.assert_called_once()

    @patch("apps.adminpanel.views.restore_backup")
    def test_restore_requires_explicit_confirmation(self, restore_backup_mock):
        self.client.force_authenticate(self.admin)
        filename = "qot-db-20260723-120000-acde1234.dump"

        response = self.client.post(
            f"/api/v1/admin-panel/backups/{filename}/restore/",
            {"confirmation": "restore"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        restore_backup_mock.assert_not_called()

    @patch("apps.adminpanel.views.restore_backup")
    def test_confirmed_restore_creates_a_safety_backup(self, restore_backup_mock):
        filename = "qot-db-20260723-120000-acde1234.dump"
        restore_backup_mock.return_value = {
            "backup": {"name": filename},
            "safety_backup": {"name": "qot-db-20260723-120100-acde5678.dump"},
        }
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            f"/api/v1/admin-panel/backups/{filename}/restore/",
            {"confirmation": "RESTORE"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("safety_backup", response.data)

    def test_moderator_cannot_access_database_backups(self):
        self.client.force_authenticate(self.moderator)

        response = self.client.get("/api/v1/admin-panel/backups/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminActivityAuditTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            phone="+256700001101",
            email="trace-admin@example.com",
            full_name="Trace Admin",
            password="test-password",
            role=User.ROLE_ADMIN,
            is_staff=True,
        )
        self.moderator = User.objects.create_user(
            phone="+256700001102",
            email="trace-moderator@example.com",
            full_name="Trace Moderator",
            password="test-password",
            role=User.ROLE_MODERATOR,
            is_staff=True,
        )
        self.user = User.objects.create_user(
            phone="+256700001103",
            email="trace-user@example.com",
            full_name="Trace User",
            password="test-password",
        )

    def test_moderator_action_is_recorded_with_actor_and_target(self):
        self.client.force_authenticate(self.moderator)

        response = self.client.post(
            f"/api/v1/admin-panel/users/{self.user.id}/ban/",
            {"banned_reason": "Repeated marketplace abuse"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        activity = AdminActivityLog.objects.get()
        self.assertEqual(activity.actor, self.moderator)
        self.assertEqual(activity.actor_role, User.ROLE_MODERATOR)
        self.assertEqual(activity.action, "user.ban")
        self.assertEqual(activity.target_id, str(self.user.id))
        self.assertEqual(activity.status_code, status.HTTP_200_OK)
        self.assertEqual(
            activity.payload["banned_reason"],
            "Repeated marketplace abuse",
        )

    def test_failed_staff_action_is_also_recorded(self):
        self.client.force_authenticate(self.moderator)

        response = self.client.post(
            f"/api/v1/admin-panel/users/{self.admin.id}/ban/",
            {"banned_reason": "Not permitted"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        activity = AdminActivityLog.objects.get()
        self.assertEqual(activity.action, "user.ban")
        self.assertEqual(activity.status_code, status.HTTP_403_FORBIDDEN)

    def test_sensitive_values_are_redacted(self):
        self.client.force_authenticate(self.admin)

        response = self.client.patch(
            f"/api/v1/admin-panel/users/{self.user.id}/",
            {"password": "must-never-be-saved", "full_name": "Updated User"},
            format="json",
        )

        self.assertIn(response.status_code, {status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST})
        activity = AdminActivityLog.objects.get()
        self.assertEqual(activity.payload["password"], "[redacted]")

    def test_report_moderation_action_is_also_recorded(self):
        self.client.force_authenticate(self.moderator)

        response = self.client.post(
            "/api/v1/moderation/reports/999999/resolve/",
            {"resolution_note": "Reviewed by moderation"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        activity = AdminActivityLog.objects.get()
        self.assertEqual(activity.action, "report.resolve")
        self.assertEqual(activity.target_type, "listing report")
        self.assertEqual(activity.target_id, "999999")
        self.assertEqual(activity.status_code, status.HTTP_404_NOT_FOUND)

    def test_only_administrators_can_view_the_system_trace(self):
        AdminActivityLog.objects.create(
            actor=self.moderator,
            actor_name=self.moderator.full_name,
            actor_email=self.moderator.email,
            actor_role=self.moderator.role,
            action="user.ban",
            description="Restricted user #10",
            method="POST",
            path="/api/v1/admin-panel/users/10/ban/",
            target_type="user",
            target_id="10",
            status_code=200,
        )

        self.client.force_authenticate(self.admin)
        admin_response = self.client.get("/api/v1/admin-panel/activity/")

        self.client.force_authenticate(self.moderator)
        moderator_response = self.client.get("/api/v1/admin-panel/activity/")

        self.assertEqual(admin_response.status_code, status.HTTP_200_OK)
        self.assertEqual(admin_response.data["summary"]["total"], 1)
        self.assertEqual(admin_response.data["results"][0]["actor_name"], "Trace Moderator")
        self.assertEqual(moderator_response.status_code, status.HTTP_403_FORBIDDEN)


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
