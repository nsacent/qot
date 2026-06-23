from rest_framework import serializers

from .models import RecentSearch, SavedSearch


class RecentSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecentSearch
        fields = [
            "id",
            "query",
            "filters",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
        ]


class SavedSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedSearch
        fields = [
            "id",
            "name",
            "query",
            "filters",
            "notify_user",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def validate_filters(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Filters must be an object.")

        return value