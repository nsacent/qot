from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.categories.models import Category
from apps.listings.models import Listing
from apps.locations.models import City, Region
from apps.notifications.models import Notification

from .models import ListingReport


class ListingReportCreateTests(APITestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            phone="+256700009001",
            email="report-seller@example.com",
            full_name="Report Seller",
            password="test-password",
            is_verified=True,
            phone_verified_at=timezone.now(),
        )
        self.reporter = User.objects.create_user(
            phone="+256700009002",
            email="reporter@example.com",
            full_name="Verified Reporter",
            password="test-password",
            is_verified=True,
            phone_verified_at=timezone.now(),
        )
        self.region = Region.objects.create(
            name="Report Test Region",
            slug="report-test-region",
        )
        self.city = City.objects.create(
            region=self.region,
            name="Report Test City",
            slug="report-test-city",
        )
        self.category = Category.objects.create(
            name="Report Test Category",
            slug="report-test-category",
        )
        self.client.force_authenticate(self.reporter)

    def create_listing(self, suffix):
        return Listing.objects.create(
            seller=self.seller,
            category=self.category,
            city=self.city,
            title=f"Report test advert {suffix}",
            slug=f"report-test-advert-{suffix}",
            description="An active advert used to test reporting.",
            price="100000.00",
            condition=Listing.CONDITION_USED,
            status=Listing.STATUS_ACTIVE,
            expires_at=timezone.now() + timedelta(days=30),
        )

    def test_every_supported_reason_can_be_submitted(self):
        for reason, _label in ListingReport.REASON_CHOICES:
            with self.subTest(reason=reason):
                listing = self.create_listing(reason)
                response = self.client.post(
                    f"/api/v1/listings/{listing.id}/report/",
                    {
                        "reason": reason,
                        "description": "This advert needs moderator review.",
                    },
                    format="json",
                )

                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                self.assertEqual(response.data["reason"], reason)
                self.assertTrue(
                    ListingReport.objects.filter(
                        listing=listing,
                        reporter=self.reporter,
                        reason=reason,
                    ).exists()
                )

    def test_unknown_reason_is_rejected(self):
        listing = self.create_listing("unknown-reason")

        response = self.client.post(
            f"/api/v1/listings/{listing.id}/report/",
            {
                "reason": "not_a_real_reason",
                "description": "This should not be accepted.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(ListingReport.objects.filter(listing=listing).exists())

    def test_admin_report_deletion_requires_reason_and_notifies_seller(self):
        listing = self.create_listing("admin-delete")
        report = ListingReport.objects.create(
            listing=listing,
            reporter=self.reporter,
            reason=ListingReport.REASON_SCAM,
            description="This reported ad requires removal.",
        )
        admin = User.objects.create_user(
            phone="+256700009099",
            email="report-admin@example.com",
            full_name="Report Admin",
            password="test-password",
            role=User.ROLE_ADMIN,
            is_staff=True,
        )
        self.client.force_authenticate(admin)
        endpoint = f"/api/v1/moderation/reports/{report.id}/delete-listing/"

        missing_reason = self.client.post(endpoint, {}, format="json")
        listing.refresh_from_db()
        self.assertEqual(missing_reason.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(listing.status, Listing.STATUS_ACTIVE)

        reason = "The ad is fraudulent and breaches QOT marketplace safety rules."
        response = self.client.post(
            endpoint,
            {"deletion_reason": reason},
            format="json",
        )
        listing.refresh_from_db()
        report.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(listing.status, Listing.STATUS_DELETED)
        self.assertTrue(report.is_resolved)
        notification = Notification.objects.get(
            user=self.seller,
            notification_type=Notification.TYPE_LISTING_DELETED,
        )
        self.assertIn(reason, notification.message)
