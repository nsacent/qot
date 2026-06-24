from django.conf import settings
from django.db import models


class Payment(models.Model):
    PURPOSE_FEATURED_LISTING = "featured_listing"
    PURPOSE_BOOST_LISTING = "boost_listing"
    PURPOSE_SUBSCRIPTION = "subscription"

    PURPOSE_CHOICES = [
        (PURPOSE_FEATURED_LISTING, "Featured Listing"),
        (PURPOSE_BOOST_LISTING, "Boost Listing"),
        (PURPOSE_SUBSCRIPTION, "Subscription"),
    ]

    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID, "Paid"),
        (STATUS_FAILED, "Failed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    METHOD_MTN = "mtn_mobile_money"
    METHOD_AIRTEL = "airtel_money"
    METHOD_CARD = "card"
    METHOD_CASH = "cash"
    METHOD_MANUAL = "manual"

    METHOD_CHOICES = [
        (METHOD_MTN, "MTN Mobile Money"),
        (METHOD_AIRTEL, "Airtel Money"),
        (METHOD_CARD, "Card"),
        (METHOD_CASH, "Cash"),
        (METHOD_MANUAL, "Manual"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments",
    )

    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
    )

    purpose = models.CharField(
        max_length=50,
        choices=PURPOSE_CHOICES,
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    currency = models.CharField(
        max_length=10,
        default="UGX",
    )

    payment_method = models.CharField(
        max_length=50,
        choices=METHOD_CHOICES,
        default=METHOD_MANUAL,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    reference = models.CharField(
        max_length=100,
        unique=True,
    )

    provider_reference = models.CharField(
        max_length=255,
        blank=True,
    )

    notes = models.TextField(blank=True)

    paid_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["reference"]),
        ]

    def __str__(self):
        return f"{self.reference} - {self.user} - {self.status}"