from types import SimpleNamespace

from django.http import JsonResponse
from django.test import RequestFactory, SimpleTestCase

from .middleware import PushDeviceRegistrationDedupeMiddleware
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


class PushDeviceRegistrationDedupeMiddlewareTests(SimpleTestCase):
    def setUp(self):
        PushDeviceRegistrationDedupeMiddleware.reset()
        self.factory = RequestFactory()
        self.calls = 0

        def response(request):
            self.calls += 1
            return JsonResponse({"registered": True}, status=201)

        self.middleware = PushDeviceRegistrationDedupeMiddleware(response)

    def request(self, device_id="qot-test-device", token="access-token"):
        return self.factory.post(
            "/api/v1/notifications/devices/",
            data="{}",
            content_type="application/json",
            HTTP_X_QOT_DEVICE_ID=device_id,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

    def test_repeated_registration_is_answered_without_calling_the_api_again(self):
        first = self.middleware(self.request())
        duplicate = self.middleware(self.request())

        self.assertEqual(first.status_code, 201)
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(self.calls, 1)

    def test_different_authenticated_device_is_not_deduplicated(self):
        self.middleware(self.request(device_id="first-device"))
        second = self.middleware(self.request(device_id="second-device"))

        self.assertEqual(second.status_code, 201)
        self.assertEqual(self.calls, 2)
