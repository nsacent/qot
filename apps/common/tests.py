from types import SimpleNamespace

from django.test import SimpleTestCase

from .permissions import IsVerifiedUser


class PrimaryVerificationPermissionTests(SimpleTestCase):
    def setUp(self):
        self.permission = IsVerifiedUser()

    def test_email_or_legacy_verification_is_not_enough(self):
        request = SimpleNamespace(
            user=SimpleNamespace(
                is_authenticated=True,
                is_verified=True,
                phone_verified=False,
            )
        )

        self.assertFalse(self.permission.has_permission(request, None))

    def test_verified_phone_allows_protected_actions(self):
        request = SimpleNamespace(
            user=SimpleNamespace(
                is_authenticated=True,
                is_verified=True,
                phone_verified=True,
            )
        )

        self.assertTrue(self.permission.has_permission(request, None))
