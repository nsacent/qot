from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings

from apps.accounts.models import User

from .models import Notification
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
