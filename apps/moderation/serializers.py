from rest_framework import serializers

from .models import ListingReport


class ListingReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingReport
        fields = [
            "id",
            "listing",
            "reason",
            "description",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "listing",
            "created_at",
        ]


class AdminListingReportSerializer(serializers.ModelSerializer):
    listing_title = serializers.CharField(source="listing.title", read_only=True)
    listing_status = serializers.CharField(source="listing.status", read_only=True)
    reporter_name = serializers.CharField(source="reporter.full_name", read_only=True)
    reporter_phone = serializers.CharField(source="reporter.phone", read_only=True)
    resolved_by_name = serializers.CharField(source="resolved_by.full_name", read_only=True)

    class Meta:
        model = ListingReport
        fields = [
            "id",
            "listing",
            "listing_title",
            "listing_status",
            "reporter",
            "reporter_name",
            "reporter_phone",
            "reason",
            "description",
            "is_resolved",
            "resolved_by",
            "resolved_by_name",
            "resolved_at",
            "created_at",
        ]
        read_only_fields = fields


class ResolveReportSerializer(serializers.Serializer):
    note = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
    )


class RejectReportedListingSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField(
        required=True,
        max_length=1000,
    )