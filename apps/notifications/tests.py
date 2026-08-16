from unittest.mock import MagicMock, patch

from django.core import mail
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User

from .models import Notification, PushDevice
from .services import create_notification


class NotificationPreferenceServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone="+256700003001",
            email="notification-user@example.com",
            full_name="Notification User",
            password="test-password",
        )

    @patch("apps.notifications.services.broadcast_notification")
    def test_disabled_preference_suppresses_notification(self, broadcast):
        preferences = self.user.profile.notification_preferences
        preferences["messages"] = False
        self.user.profile.notification_preferences = preferences
        self.user.profile.save(update_fields=["notification_preferences"])

        result = create_notification(
            user=self.user,
            notification_type=Notification.TYPE_MESSAGE,
            title="New message",
            message="A test message.",
            preference_key="messages",
        )

        self.assertIsNone(result)
        self.assertFalse(Notification.objects.filter(user=self.user).exists())
        broadcast.assert_not_called()

    @patch("apps.notifications.services.broadcast_notification")
    def test_enabled_preference_creates_notification(self, broadcast):
        result = create_notification(
            user=self.user,
            notification_type=Notification.TYPE_MESSAGE,
            title="New message",
            message="A test message.",
            preference_key="messages",
        )

        self.assertIsNotNone(result)
        self.assertTrue(Notification.objects.filter(user=self.user).exists())
        broadcast.assert_called_once_with(result)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="QOT Uganda <info@qot.ug>",
    )
    @patch("apps.notifications.services.broadcast_notification")
    def test_created_notification_is_also_emailed(self, broadcast):
        with self.captureOnCommitCallbacks(execute=True):
            notification = create_notification(
                user=self.user,
                notification_type=Notification.TYPE_FAVORITE,
                title="Someone saved your ad",
                message="A buyer saved your ad.",
            )

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])
        self.assertIn(notification.title, mail.outbox[0].subject)
        self.assertIn("A buyer saved your ad.", mail.outbox[0].body)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    @patch("apps.notifications.services.requests.post")
    @patch("apps.notifications.services.broadcast_notification")
    def test_created_notification_is_sent_to_registered_devices(self, broadcast, post):
        PushDevice.objects.create(
            user=self.user,
            expo_push_token="ExponentPushToken[test-device]",
            platform=PushDevice.PLATFORM_ANDROID,
        )
        response = MagicMock()
        response.json.return_value = {"data": [{"status": "ok", "id": "ticket-1"}]}
        post.return_value = response

        with self.captureOnCommitCallbacks(execute=True):
            notification = create_notification(
                user=self.user,
                notification_type=Notification.TYPE_MESSAGE,
                title="New message",
                message="A buyer replied to your ad.",
                image_url="https://api.qot.ug/media/push/message.jpg",
            )

        payload = post.call_args.kwargs["json"][0]
        self.assertEqual(payload["to"], "ExponentPushToken[test-device]")
        self.assertEqual(payload["data"]["notification_id"], notification.id)
        self.assertEqual(payload["data"]["url"], "qot://notifications")
        self.assertEqual(payload["badge"], 1)
        self.assertEqual(
            payload["richContent"],
            {"image": "https://api.qot.ug/media/push/message.jpg"},
        )


class PushDeviceAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone="+256700003010",
            email="push-device@example.com",
            full_name="Push Device User",
            password="test-password",
        )
        self.client.force_authenticate(self.user)

    def test_device_can_be_registered_and_disabled(self):
        payload = {
            "expo_push_token": "ExponentPushToken[registered-device]",
            "platform": "android",
            "device_id": "physical-phone",
        }
        registered = self.client.post(
            "/api/v1/notifications/devices/",
            payload,
            format="json",
        )
        self.assertEqual(registered.status_code, status.HTTP_201_CREATED)
        self.assertTrue(PushDevice.objects.get(user=self.user).is_active)

        registered_again = self.client.post(
            "/api/v1/notifications/devices/",
            payload,
            format="json",
        )
        self.assertEqual(registered_again.status_code, status.HTTP_200_OK)
        self.assertEqual(PushDevice.objects.filter(expo_push_token=payload["expo_push_token"]).count(), 1)

        disabled = self.client.delete(
            "/api/v1/notifications/devices/",
            {"expo_push_token": payload["expo_push_token"]},
            format="json",
        )
        self.assertEqual(disabled.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(PushDevice.objects.get(user=self.user).is_active)

        reactivated = self.client.post(
            "/api/v1/notifications/devices/",
            payload,
            format="json",
        )
        self.assertEqual(reactivated.status_code, status.HTTP_200_OK)
        self.assertTrue(PushDevice.objects.get(user=self.user).is_active)

    def test_invalid_push_token_is_rejected(self):
        response = self.client.post(
            "/api/v1/notifications/devices/",
            {"expo_push_token": "not-a-token", "platform": "android"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AdminNotificationEmailTests(TestCase):
    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        ADMIN_NOTIFICATION_EMAILS=["info@qot.ug"],
    )
    def test_new_signup_alerts_configured_admin_email(self):
        with self.captureOnCommitCallbacks(execute=True):
            user = User.objects.create_user(
                phone="+256700003002",
                email="new-member@example.com",
                full_name="New QOT Member",
                password="test-password",
            )

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["info@qot.ug"])
        self.assertIn("New user signup", mail.outbox[0].subject)
        self.assertIn(user.full_name, mail.outbox[0].body)
