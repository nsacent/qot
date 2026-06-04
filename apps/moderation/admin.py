from django.contrib import admin

from .models import ListingReport


@admin.register(ListingReport)
class ListingReportAdmin(admin.ModelAdmin):
    list_display = [
        "listing",
        "reporter",
        "reason",
        "is_resolved",
        "resolved_by",
        "created_at",
        "resolved_at",
    ]

    list_filter = [
        "reason",
        "is_resolved",
        "created_at",
        "resolved_at",
    ]

    search_fields = [
        "listing__title",
        "reporter__phone",
        "reporter__email",
        "reporter__full_name",
        "description",
        "resolution_note",
    ]

    readonly_fields = [
        "created_at",
        "resolved_at",
    ]