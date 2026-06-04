from rest_framework import serializers

from .models import ListingReport


class ListingReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingReport
        fields = [
            "reason",
            "description",
        ]

    def validate_description(self, value):
        if value and len(value) > 1000:
            raise serializers.ValidationError(
                "Description cannot exceed 1000 characters."
            )
        return value


class ListingReportSerializer(serializers.ModelSerializer):
    listing_title = serializers.CharField(source="listing.title", read_only=True)
    reporter_name = serializers.CharField(source="reporter.full_name", read_only=True)
    reporter_phone = serializers.CharField(source="reporter.phone", read_only=True)
    resolved_by_name = serializers.CharField(source="resolved_by.full_name", read_only=True)

    class Meta:
        model = ListingReport
        fields = [
            "id",
            "listing",
            "listing_title",
            "reporter",
            "reporter_name",
            "reporter_phone",
            "reason",
            "description",
            "is_resolved",
            "resolved_by",
            "resolved_by_name",
            "resolution_note",
            "created_at",
            "resolved_at",
        ]
        read_only_fields = fields


class ListingReportResolveSerializer(serializers.Serializer):
    resolution_note = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
    )