from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User


class RegistrationTests(APITestCase):
    register_url = "/api/v1/auth/register/"

    def registration_data(self, phone):
        digits = "".join(character for character in phone if character.isdigit())

        return {
            "phone": phone,
            "email": f"user-{digits[-6:]}@example.com",
            "full_name": "Ugandan User",
            "password": "strong-test-password",
            "password_confirm": "strong-test-password",
        }

    def test_registration_normalizes_local_ugandan_phone_number(self):
        response = self.client.post(
            self.register_url,
            self.registration_data("0700 000 123"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"]["phone"], "+256700000123")
        self.assertTrue(User.objects.filter(phone="+256700000123").exists())

    def test_registration_normalizes_ugandan_country_code(self):
        response = self.client.post(
            self.register_url,
            self.registration_data("256 701 000 123"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"]["phone"], "+256701000123")

    def test_registration_rejects_non_ugandan_phone_number(self):
        response = self.client.post(
            self.register_url,
            self.registration_data("+254700000123"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            str(response.data["phone"][0]),
            "Enter a valid Ugandan mobile number, such as +256700000001.",
        )

    def test_registration_rejects_duplicate_phone_after_normalizing(self):
        User.objects.create_user(
            phone="+256702000123",
            email="existing@example.com",
            full_name="Existing User",
            password="strong-test-password",
        )

        response = self.client.post(
            self.register_url,
            self.registration_data("0702 000 123"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            str(response.data["phone"][0]),
            "An account with this phone number already exists.",
        )


class AuthenticationSessionTests(APITestCase):
    login_url = "/api/v1/auth/login/"
    refresh_url = "/api/v1/auth/token/refresh/"

    def setUp(self):
        self.user = User.objects.create_user(
            phone="+256700000099",
            email="session-test@example.com",
            full_name="Session Test",
            password="strong-test-password",
        )

    def login(self, keep_signed_in=False):
        return self.client.post(
            self.login_url,
            {
                "identifier": self.user.email,
                "password": "strong-test-password",
                "keep_signed_in": keep_signed_in,
            },
            format="json",
        )

    def test_normal_login_uses_standard_refresh_lifetime(self):
        response = self.login()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        refresh = RefreshToken(response.data["tokens"]["refresh"])
        lifetime = timedelta(seconds=refresh["exp"] - refresh["iat"])

        self.assertNotIn("keep_signed_in", refresh)
        self.assertEqual(
            lifetime,
            settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"],
        )

    def test_keep_signed_in_lifetime_survives_refresh_rotation(self):
        login_response = self.login(keep_signed_in=True)

        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        refresh = RefreshToken(login_response.data["tokens"]["refresh"])
        login_lifetime = timedelta(seconds=refresh["exp"] - refresh["iat"])

        self.assertTrue(refresh["keep_signed_in"])
        self.assertEqual(login_lifetime, settings.KEEP_SIGNED_IN_LIFETIME)

        refresh_response = self.client.post(
            self.refresh_url,
            {"refresh": str(refresh)},
            format="json",
        )

        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        rotated = RefreshToken(refresh_response.data["refresh"])
        rotated_lifetime = timedelta(seconds=rotated["exp"] - rotated["iat"])

        self.assertTrue(rotated["keep_signed_in"])
        self.assertEqual(rotated_lifetime, settings.KEEP_SIGNED_IN_LIFETIME)

    def test_wrong_password_returns_a_clear_error(self):
        response = self.client.post(
            self.login_url,
            {
                "identifier": self.user.email,
                "password": "wrong-password",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.data["detail"],
            "The phone/email or password is incorrect.",
        )

    def test_inactive_account_returns_a_clear_error(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        response = self.login()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.data["detail"],
            "This account is inactive. Please contact QOT support.",
        )

    def test_banned_account_returns_a_clear_error(self):
        self.user.is_banned = True
        self.user.save(update_fields=["is_banned"])

        response = self.login()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.data["detail"],
            "This account has been banned. Please contact QOT support.",
        )


class NotificationPreferenceTests(APITestCase):
    me_url = "/api/v1/auth/me/"

    def setUp(self):
        self.user = User.objects.create_user(
            phone="+256700000088",
            email="preferences@example.com",
            full_name="Preference User",
            password="strong-test-password",
            is_verified=True,
        )
        self.client.force_authenticate(self.user)

    def test_notification_preferences_are_saved_on_the_profile(self):
        preferences = {
            "verification": True,
            "messages": False,
            "listing_approvals": True,
            "listing_rejections": True,
            "reports": True,
            "renewals": False,
            "marketing": True,
        }

        response = self.client.patch(
            self.me_url,
            {"profile": {"notification_preferences": preferences}},
            format="json",
        )
        self.user.profile.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.user.profile.notification_preferences, preferences)

    def test_notification_preferences_reject_unknown_keys(self):
        response = self.client.patch(
            self.me_url,
            {"profile": {"notification_preferences": {"unknown": True}}},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("notification_preferences", response.data["profile"])


@override_settings(GOOGLE_OAUTH_CLIENT_ID="qot-test.apps.googleusercontent.com")
class GoogleAuthenticationTests(APITestCase):
    google_url = "/api/v1/auth/google/"

    def google_identity(self, **overrides):
        identity = {
            "sub": "google-user-123",
            "email": "google-user@example.com",
            "email_verified": True,
            "name": "Google User",
            "iss": "https://accounts.google.com",
            "aud": settings.GOOGLE_OAUTH_CLIENT_ID,
        }
        identity.update(overrides)
        return identity

    @patch("apps.accounts.serializers.google_id_token.verify_oauth2_token")
    def test_google_sign_in_creates_verified_user_and_session(self, verify_token):
        verify_token.return_value = self.google_identity()

        response = self.client.post(
            self.google_url,
            {"credential": "valid-google-token", "keep_signed_in": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = User.objects.get(email="google-user@example.com")
        refresh = RefreshToken(response.data["tokens"]["refresh"])

        self.assertEqual(user.google_sub, "google-user-123")
        self.assertTrue(user.is_verified)
        self.assertFalse(user.has_usable_password())
        self.assertTrue(refresh["keep_signed_in"])
        verify_token.assert_called_once()
        verify_args = verify_token.call_args.args
        self.assertEqual(verify_args[0], "valid-google-token")
        self.assertEqual(verify_args[2], settings.GOOGLE_OAUTH_CLIENT_ID)

    @patch("apps.accounts.serializers.google_id_token.verify_oauth2_token")
    def test_google_sign_in_links_existing_email_account(self, verify_token):
        user = User.objects.create_user(
            email="google-user@gmail.com",
            full_name="Existing User",
            password="existing-password",
        )
        verify_token.return_value = self.google_identity(
            email="google-user@gmail.com"
        )

        response = self.client.post(
            self.google_url,
            {"credential": "valid-google-token"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.google_sub, "google-user-123")
        self.assertTrue(user.is_verified)
        self.assertTrue(user.has_usable_password())

    @patch("apps.accounts.serializers.google_id_token.verify_oauth2_token")
    def test_google_sign_in_does_not_auto_link_third_party_email(
        self,
        verify_token,
    ):
        user = User.objects.create_user(
            email="google-user@example.com",
            full_name="Existing User",
            password="existing-password",
        )
        verify_token.return_value = self.google_identity()

        response = self.client.post(
            self.google_url,
            {"credential": "valid-google-token"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        user.refresh_from_db()
        self.assertIsNone(user.google_sub)
        self.assertTrue(user.has_usable_password())

    @patch("apps.accounts.serializers.google_id_token.verify_oauth2_token")
    def test_google_sign_in_rejects_unverified_email(self, verify_token):
        verify_token.return_value = self.google_identity(email_verified=False)

        response = self.client.post(
            self.google_url,
            {"credential": "unverified-google-token"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="google-user@example.com").exists())
