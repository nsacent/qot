from django.conf import settings
from django.db import models
from django.utils import timezone


class Listing(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_PENDING = "pending"
    STATUS_ACTIVE = "active"
    STATUS_UNAVAILABLE = "unavailable"
    STATUS_REJECTED = "rejected"
    STATUS_SOLD = "sold"
    STATUS_EXPIRED = "expired"
    STATUS_DELETED = "deleted"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_PENDING, "Pending Approval"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_UNAVAILABLE, "Unavailable"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_SOLD, "Sold"),
        (STATUS_EXPIRED, "Expired"),
        (STATUS_DELETED, "Deleted"),
    ]

    CONDITION_NEW = "new"
    CONDITION_USED = "used"

    CONDITION_CHOICES = [
        (CONDITION_NEW, "New"),
        (CONDITION_USED, "Used"),
    ]

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="listings",
    )

    category = models.ForeignKey(
        "categories.Category",
        on_delete=models.PROTECT,
        related_name="listings",
    )

    city = models.ForeignKey(
        "locations.City",
        on_delete=models.PROTECT,
        related_name="listings",
    )

    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=220, db_index=True)

    description = models.TextField()

    price = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=10, default="UGX")

    condition = models.CharField(
        max_length=20,
        choices=CONDITION_CHOICES,
        default=CONDITION_USED,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )

    is_negotiable = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    
    featured_until = models.DateTimeField(
        null=True,
        blank=True,
    )

    views_count = models.PositiveIntegerField(default=0)
    favorites_count = models.PositiveIntegerField(default=0)

    expires_at = models.DateTimeField(null=True, blank=True)
    sold_at = models.DateTimeField(null=True, blank=True)

    rejection_reason = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["category", "status"]),
            models.Index(fields=["city", "status"]),
            models.Index(fields=["seller", "status"]),
            models.Index(fields=["price"]),
        ]

    def __str__(self):
        return self.title

    def mark_sold(self):
        self.status = self.STATUS_SOLD
        self.sold_at = timezone.now()
        self.save(update_fields=["status", "sold_at", "updated_at"])

    def soft_delete(self):
        self.status = self.STATUS_DELETED
        self.save(update_fields=["status", "updated_at"])


class ListingImage(models.Model):
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="images",
    )

    image = models.ImageField(upload_to="listings/images/")
    content_hash = models.CharField(max_length=64, blank=True, default="", db_index=True)
    is_watermarked = models.BooleanField(default=False, db_index=True)
    is_primary = models.BooleanField(default=False)

    sort_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "id"]
        indexes = [
            models.Index(fields=["listing", "is_primary"]),
        ]

    def __str__(self):
        return f"Image for {self.listing.title}"


class PendingListingImage(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pending_listing_images",
    )
    image = models.ImageField(upload_to="listings/images/")
    content_hash = models.CharField(max_length=64, blank=True, default="", db_index=True)
    is_watermarked = models.BooleanField(default=False, db_index=True)
    reserved_for_draft = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"Pending listing image for {self.user_id}"


class ListingDraft(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="listing_draft",
    )
    data = models.JSONField(default=dict, blank=True)
    staged_image_ids = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Listing draft for {self.user_id}"


class ListingAttribute(models.Model):
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="attributes",
    )

    category_filter = models.ForeignKey(
        "categories.CategoryFilter",
        on_delete=models.PROTECT,
        related_name="listing_attributes",
    )

    value_text = models.TextField(null=True, blank=True)
    value_number = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )
    value_boolean = models.BooleanField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["listing", "category_filter"]
        indexes = [
            models.Index(fields=["category_filter"]),
        ]

    def __str__(self):
        return f"{self.listing.title} - {self.category_filter.name}"
