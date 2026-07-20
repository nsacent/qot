from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.categories.models import Category
from apps.listings.models import Listing
from apps.locations.models import City, Region

from .models import Payment, PromotionPackage


class PaymentCreationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone="+256700002001",
            full_name="Payment User",
            password="test-password",
            is_verified=True,
        )
        region = Region.objects.create(name="Payment Region", slug="payment-region")
        city = City.objects.create(
            region=region,
            name="Payment City",
            slug="payment-city",
        )
        category = Category.objects.create(
            name="Payment Category",
            slug="payment-category",
        )
        self.listing = Listing.objects.create(
            seller=self.user,
            category=category,
            city=city,
            title="Payment listing",
            slug="payment-listing",
            description="Listing for payment tests.",
            price="50000.00",
            status=Listing.STATUS_ACTIVE,
        )
        self.package = PromotionPackage.objects.create(
            name="Seven day feature",
            package_type=PromotionPackage.TYPE_FEATURED_LISTING,
            duration_days=7,
            price="25000.00",
            currency="UGX",
        )
        self.client.force_authenticate(self.user)

    def test_payment_requires_package(self):
        response = self.client.post(
            "/api/v1/payments/",
            {
                "listing": self.listing.id,
                "purpose": Payment.PURPOSE_FEATURED_LISTING,
                "amount": "1.00",
                "currency": "UGX",
                "payment_method": Payment.METHOD_MTN,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("package", response.data)

    def test_payment_uses_server_package_price_and_purpose(self):
        response = self.client.post(
            "/api/v1/payments/",
            {
                "listing": self.listing.id,
                "package": self.package.id,
                "purpose": Payment.PURPOSE_SUBSCRIPTION,
                "amount": "1.00",
                "currency": "USD",
                "payment_method": Payment.METHOD_MTN,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        payment = Payment.objects.get(user=self.user)
        self.assertEqual(payment.purpose, self.package.package_type)
        self.assertEqual(payment.amount, Decimal(self.package.price))
        self.assertEqual(payment.currency, self.package.currency)
