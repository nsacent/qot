from django.conf import settings
from django.db import models


class ListingReport(models.Model):
    REASON_SCAM = "scam"
    REASON_DUPLICATE = "duplicate"
    REASON_WRONG_CATEGORY = "wrong_category"
    REASON_PROHIBITED = "prohibited"
    REASON_SOLD_BUT_ACTIVE = "sold_but_active"
    REASON_OTHER = "other"

    REASON_CHOICES = [
        (REASON_SCAM, "Scam or Fraud"),
        (REASON_DUPLICATE, "Duplicate Listing"),
        (REASON_WRONG_CATEGORY, "Wrong Category"),
        (REASON_PROHIBITED, "Prohibited Item"),
        (REASON_SOLD_BUT_ACTIVE, "Sold but Still Active"),
        (REASON_OTHER, "Other"),
    ]

    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.CASCADE,
        related_name="reports",
    )

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="listing_reports",
    )

    reason = models.CharField(
        max_length=50,
        choices=REASON_CHOICES,
        db_index=True,
    )

    description = models.TextField(null=True, blank=True)

    is_resolved = models.BooleanField(default=False, db_index=True)

    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_listing_reports",
    )

    resolution_note = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ["listing", "reporter", "reason"]
        indexes = [
            models.Index(fields=["listing", "is_resolved"]),
            models.Index(fields=["reporter", "created_at"]),
            models.Index(fields=["reason", "is_resolved"]),
        ]

    def __str__(self):
        return f"{self.listing} reported by {self.reporter}"