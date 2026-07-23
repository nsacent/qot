from datetime import timedelta
from io import BytesIO
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import override_settings
from django.utils import timezone
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.locations.models import City, Region

from .models import User, VerificationCode
from .sms import send_sms


class CanonicalPhoneStorageTests(APITestCase):
    def test_user_manager_stores_local_number_in_canonical_format(self):
        user = User.objects.create_user(
            phone="0702 912 148",
            full_name="Canonical Number",
            password="test-password",
        )

        self.assertEqual(user.phone, "+256702912148")

    def test_model_save_normalizes_country_code_without_plus(self):
        user = User(
            phone="256702912149",
            full_name="Canonical Model Number",
        )
        user.set_password("test-password")
        user.save()

        self.assertEqual(user.phone, "+256702912149")

    def test_phone_variants_cannot_create_duplicate_accounts(self):
        User.objects.create_user(
            phone="+256702912150",
            full_name="First Account",
            password="test-password",
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(
                    phone="0702912150",
                    full_name="Duplicate Account",
                    password="test-password",
                )

    def test_database_constraint_rejects_noncanonical_bulk_write(self):
        user = User.objects.create_user(
            phone="+256702912151",
            full_name="Constraint Account",
            password="test-password",
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.filter(pk=user.pk).update(phone="0702912151")

    def test_invalid_mobile_number_is_rejected_by_model_save(self):
        user = User(phone="+256312345678", full_name="Invalid Number")

        with self.assertRaises(ValidationError):
            user.save()


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


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    FRONTEND_URL="https://qot.ug",
)
class PasswordResetRequestTests(APITestCase):
    def test_reset_email_uses_the_account_route(self):
        user = User.objects.create_user(
            phone="+256700000444",
            email="password-reset@example.com",
            full_name="Password Reset User",
            password="strong-test-password",
        )

        response = self.client.post(
            "/api/v1/auth/password-reset/request/",
            {"email": user.email},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(
            "https://qot.ug/account/reset-password?uid=",
            mail.outbox[0].body,
        )


@override_settings(
    AFRICAS_TALKING_USERNAME="qot-test",
    AFRICAS_TALKING_API_KEY="test-api-key",
    AFRICAS_TALKING_SENDER_ID="QOT",
    PHONE_OTP_EXPIRY_MINUTES=10,
    PHONE_OTP_RESEND_SECONDS=60,
    PHONE_OTP_MAX_SENDS_PER_HOUR=5,
    PHONE_OTP_MAX_ATTEMPTS=5,
)
class PhoneVerificationTests(APITestCase):
    send_url = "/api/v1/auth/verification/send/"
    confirm_url = "/api/v1/auth/verification/confirm/"

    def setUp(self):
        self.user = User.objects.create_user(
            phone="+256700000321",
            email="phone-verification@example.com",
            full_name="Phone Verification User",
            password="strong-test-password",
        )
        self.client.force_authenticate(self.user)

    def code_from_sms_mock(self, sms_mock):
        message = sms_mock.call_args.args[1]
        match = re.search(r"\b(\d{6})\b", message)
        self.assertIsNotNone(match)
        return match.group(1)

    def code_from_email_mock(self, email_mock):
        message = email_mock.call_args.kwargs["message"]
        match = re.search(r"\b(\d{6})\b", message)
        self.assertIsNotNone(match)
        return match.group(1)

    @patch("apps.accounts.services.send_sms")
    def test_phone_otp_is_sent_and_only_a_hash_is_stored(self, sms_mock):
        response = self.client.post(
            self.send_url,
            {"channel": "phone"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["channel"], "phone")
        self.assertNotIn(self.user.phone, response.data["destination"])
        sms_mock.assert_called_once()

        code = self.code_from_sms_mock(sms_mock)
        verification = VerificationCode.objects.get(user=self.user)

        self.assertNotEqual(verification.code, code)
        self.assertTrue(check_password(code, verification.code))
        self.assertEqual(verification.channel, VerificationCode.CHANNEL_PHONE)

    @patch("apps.accounts.services.send_sms")
    def test_correct_phone_otp_verifies_the_number_and_account(self, sms_mock):
        self.client.post(self.send_url, {"channel": "phone"}, format="json")
        code = self.code_from_sms_mock(sms_mock)

        response = self.client.post(
            self.confirm_url,
            {"channel": "phone", "code": code},
            format="json",
        )

        self.user.refresh_from_db()
        verification = VerificationCode.objects.get(user=self.user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.user.is_verified)
        self.assertTrue(self.user.phone_verified)
        self.assertTrue(verification.is_used)

    @patch("apps.accounts.services.send_mail")
    def test_email_otp_is_available_as_a_secondary_channel(self, email_mock):
        response = self.client.post(
            self.send_url,
            {"channel": "email"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["channel"], "email")
        self.assertNotIn(self.user.email, response.data["destination"])
        email_mock.assert_called_once()

        code = self.code_from_email_mock(email_mock)
        verification = VerificationCode.objects.get(user=self.user)

        self.assertNotEqual(verification.code, code)
        self.assertTrue(check_password(code, verification.code))
        self.assertEqual(verification.channel, VerificationCode.CHANNEL_EMAIL)

    @patch("apps.accounts.services.send_mail")
    def test_correct_email_otp_marks_email_without_marking_phone(self, email_mock):
        self.client.post(self.send_url, {"channel": "email"}, format="json")
        code = self.code_from_email_mock(email_mock)

        response = self.client.post(
            self.confirm_url,
            {"channel": "email", "code": code},
            format="json",
        )

        self.user.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.user.is_verified)
        self.assertTrue(self.user.email_verified)
        self.assertFalse(self.user.phone_verified)

    @patch("apps.accounts.services.send_sms")
    def test_resend_cooldown_returns_retry_time_without_another_sms(self, sms_mock):
        first_response = self.client.post(
            self.send_url,
            {"channel": "phone"},
            format="json",
        )
        second_response = self.client.post(
            self.send_url,
            {"channel": "phone"},
            format="json",
        )

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            second_response.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )
        self.assertGreater(second_response.data["retry_after"], 0)
        sms_mock.assert_called_once()

    @patch("apps.accounts.services.send_sms")
    def test_five_wrong_codes_lock_the_current_otp(self, sms_mock):
        self.client.post(self.send_url, {"channel": "phone"}, format="json")
        code = self.code_from_sms_mock(sms_mock)
        wrong_code = "000000" if code != "000000" else "111111"

        response = None

        for _ in range(5):
            response = self.client.post(
                self.confirm_url,
                {"channel": "phone", "code": wrong_code},
                format="json",
            )

        verification = VerificationCode.objects.get(user=self.user)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Too many incorrect attempts", response.data["detail"])
        self.assertEqual(verification.failed_attempts, 5)
        self.assertTrue(verification.is_used)

    @patch("apps.accounts.services.send_sms")
    def test_expired_phone_otp_is_rejected(self, sms_mock):
        self.client.post(self.send_url, {"channel": "phone"}, format="json")
        code = self.code_from_sms_mock(sms_mock)
        VerificationCode.objects.filter(user=self.user).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )

        response = self.client.post(
            self.confirm_url,
            {"channel": "phone", "code": code},
            format="json",
        )

        self.user.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("expired", response.data["detail"])
        self.assertFalse(self.user.is_verified)

    @override_settings(
        AFRICAS_TALKING_USERNAME="",
        AFRICAS_TALKING_API_KEY="",
    )
    def test_missing_sms_configuration_returns_a_safe_error(self):
        response = self.client.post(
            self.send_url,
            {"channel": "phone"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
        self.assertNotIn("api", str(response.data).lower())

    def test_changing_phone_number_removes_phone_verification(self):
        self.user.is_verified = True
        self.user.phone_verified_at = timezone.now()
        self.user.save(update_fields=["is_verified", "phone_verified_at"])

        response = self.client.patch(
            "/api/v1/auth/me/",
            {"phone": "+256701000321"},
            format="json",
        )

        self.user.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.user.phone, "+256701000321")
        self.assertFalse(self.user.is_verified)
        self.assertIsNone(self.user.phone_verified_at)


@override_settings(
    AFRICAS_TALKING_USERNAME="qot-production",
    AFRICAS_TALKING_API_KEY="test-api-key",
    AFRICAS_TALKING_SENDER_ID="QOT",
    AFRICAS_TALKING_SANDBOX=False,
)
class AfricasTalkingSMSTests(APITestCase):
    @patch("apps.accounts.sms.requests.post")
    def test_sms_provider_posts_to_africas_talking(self, post):
        post.return_value.json.return_value = {
            "SMSMessageData": {
                "Recipients": [
                    {
                        "messageId": "ATXid_test",
                        "status": "Success",
                        "statusCode": 101,
                        "cost": "UGX 35",
                    }
                ]
            }
        }

        result = send_sms("+256700000321", "QOT test message")

        self.assertEqual(result["message_id"], "ATXid_test")
        post.assert_called_once()
        request = post.call_args
        self.assertEqual(
            request.args[0],
            "https://api.africastalking.com/version1/messaging",
        )
        self.assertEqual(request.kwargs["data"]["username"], "qot-production")
        self.assertEqual(request.kwargs["data"]["to"], "+256700000321")
        self.assertEqual(request.kwargs["data"]["from"], "QOT")
        self.assertEqual(request.kwargs["headers"]["apiKey"], "test-api-key")


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

    def test_login_normalizes_a_local_ugandan_phone_number(self):
        response = self.client.post(
            self.login_url,
            {
                "identifier": "0700 000 099",
                "password": "strong-test-password",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["phone"], "+256700000099")

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

    def test_email_cannot_be_changed_from_the_user_profile(self):
        original_email = self.user.email

        response = self.client.patch(
            self.me_url,
            {"email": "changed@example.com"},
            format="json",
        )

        self.user.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.user.email, original_email)
        self.assertEqual(response.data["email"], original_email)

    def test_default_city_is_saved_and_returned_with_region(self):
        region = Region.objects.create(name="Central", slug="central-profile")
        city = City.objects.create(region=region, name="Kampala", slug="kampala-profile")

        response = self.client.patch(
            self.me_url,
            {"profile": {"default_city": city.id}},
            format="json",
        )
        self.user.profile.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.user.profile.default_city, city)

        me_response = self.client.get(self.me_url)
        self.assertEqual(me_response.data["profile"]["default_city"], city.id)
        self.assertEqual(me_response.data["profile"]["default_city_name"], "Kampala")
        self.assertEqual(me_response.data["profile"]["default_region_name"], "Central")

    def test_timezone_is_saved_and_returned(self):
        response = self.client.patch(
            self.me_url,
            {"timezone": "Africa/Nairobi"},
            format="json",
        )
        self.user.profile.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.user.profile.timezone, "Africa/Nairobi")
        self.assertEqual(response.data["profile"]["timezone"], "Africa/Nairobi")

    def test_invalid_timezone_is_rejected(self):
        response = self.client.patch(
            self.me_url,
            {"timezone": "Africa/Not-A-Place"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("timezone", response.data)


class ProfileMediaTests(APITestCase):
    me_url = "/api/v1/auth/me/"

    def setUp(self):
        self.media_directory = TemporaryDirectory()
        self.media_override = override_settings(MEDIA_ROOT=Path(self.media_directory.name))
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.addCleanup(self.media_directory.cleanup)

        self.user = User.objects.create_user(
            phone="+256700000077",
            email="profile-media@example.com",
            full_name="Profile Media User",
            password="strong-test-password",
            is_verified=True,
        )
        self.client.force_authenticate(self.user)

    def image_upload(self, name):
        image_bytes = BytesIO()
        Image.new("RGB", (4, 4), color=(249, 115, 22)).save(image_bytes, format="PNG")
        return SimpleUploadedFile(name, image_bytes.getvalue(), content_type="image/png")

    def test_avatar_and_cover_photo_accept_multipart_uploads(self):
        response = self.client.patch(
            self.me_url,
            {
                "avatar": self.image_upload("avatar.png"),
                "cover_photo": self.image_upload("cover.png"),
                "bio": "Trusted local seller",
            },
            format="multipart",
        )
        self.user.profile.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.user.profile.avatar.name.startswith("users/avatars/"))
        self.assertTrue(self.user.profile.cover_photo.name.startswith("users/covers/"))
        self.assertEqual(self.user.profile.bio, "Trusted local seller")


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
