from django.conf import settings
from django.db import models


class SellerReview(models.Model):
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="given_reviews",
    )

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_reviews",
    )

    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviews",
    )

    rating = models.PositiveSmallIntegerField()
    item_accuracy_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    item_condition_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    communication_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    comment = models.TextField(blank=True)

    is_visible = models.BooleanField(default=True)
    is_verified_transaction = models.BooleanField(default=False, db_index=True)
    verified_offer = models.OneToOneField(
        "chats.ChatMessage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transaction_review",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ["reviewer", "seller", "listing"]
        indexes = [
            models.Index(fields=["seller", "-created_at"]),
            models.Index(fields=["reviewer", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.reviewer} reviewed {self.seller} - {self.rating}"
