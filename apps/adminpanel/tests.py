from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User


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
