from rest_framework import serializers

from apps.accounts.models import User
from apps.listings.models import Listing


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "phone",
            "email",
            "full_name",
            "role",
            "is_active",
            "is_verified",
            "is_banned",
            "banned_reason",
            "is_staff",
            "date_joined",
        ]


class AdminListingSerializer(serializers.ModelSerializer):
    seller_name = serializers.CharField(source="seller.full_name", read_only=True)
    seller_phone = serializers.CharField(source="seller.phone", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)

    class Meta:
        model = Listing
        fields = [
            "id",
            "title",
            "slug",
            "seller",
            "seller_name",
            "seller_phone",
            "category",
            "category_name",
            "city",
            "city_name",
            "price",
            "currency",
            "condition",
            "status",
            "is_featured",
            "featured_until",
            "views_count",
            "favorites_count",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]


class ListingRejectSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField(
        max_length=1000,
        required=True,
    )


class UserBanSerializer(serializers.Serializer):
    banned_reason = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True,
    )

class FeatureListingSerializer(serializers.Serializer):
    days = serializers.IntegerField(
        min_value=1,
        max_value=365,
        default=7,
    )