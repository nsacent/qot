from django.contrib import admin

from .models import Listing, ListingImage, ListingAttribute


class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 1


class ListingAttributeInline(admin.TabularInline):
    model = ListingAttribute
    extra = 1


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "seller",
        "category",
        "city",
        "price",
        "currency",
        "status",
        "is_featured",
        "views_count",
        "created_at",
    ]

    list_filter = [
        "status",
        "category",
        "city",
        "condition",
        "is_featured",
        "created_at",
    ]

    search_fields = [
        "title",
        "description",
        "seller__phone",
        "seller__email",
        "seller__full_name",
        "category__name",
        "city__name",
    ]

    prepopulated_fields = {
        "slug": ("title",),
    }

    readonly_fields = [
        "views_count",
        "favorites_count",
        "sold_at",
        "created_at",
        "updated_at",
    ]

    inlines = [
        ListingImageInline,
        ListingAttributeInline,
    ]

    actions = [
        "approve_listings",
        "reject_listings",
        "mark_as_sold",
        "mark_as_featured",
        "remove_featured",
    ]

    def approve_listings(self, request, queryset):
        queryset.update(status=Listing.STATUS_ACTIVE)

    approve_listings.short_description = "Approve selected listings"

    def reject_listings(self, request, queryset):
        queryset.update(status=Listing.STATUS_REJECTED)

    reject_listings.short_description = "Reject selected listings"

    def mark_as_sold(self, request, queryset):
        for listing in queryset:
            listing.mark_sold()

    mark_as_sold.short_description = "Mark selected listings as sold"

    def mark_as_featured(self, request, queryset):
        queryset.update(is_featured=True)

    mark_as_featured.short_description = "Mark selected listings as featured"

    def remove_featured(self, request, queryset):
        queryset.update(is_featured=False)

    remove_featured.short_description = "Remove featured status"


@admin.register(ListingImage)
class ListingImageAdmin(admin.ModelAdmin):
    list_display = [
        "listing",
        "is_primary",
        "sort_order",
        "created_at",
    ]

    list_filter = [
        "is_primary",
        "created_at",
    ]

    search_fields = [
        "listing__title",
    ]


@admin.register(ListingAttribute)
class ListingAttributeAdmin(admin.ModelAdmin):
    list_display = [
        "listing",
        "category_filter",
        "value_text",
        "value_number",
        "value_boolean",
        "created_at",
    ]

    list_filter = [
        "category_filter",
        "created_at",
    ]

    search_fields = [
        "listing__title",
        "category_filter__name",
    ]