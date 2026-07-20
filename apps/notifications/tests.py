from unittest.mock import patch

from django.test import TestCase

from apps.accounts.models import User

from .models import Notification
from .services import create_notification


class NotificationPreferenceServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone="+256700003001",
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
