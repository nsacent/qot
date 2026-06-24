from rest_framework import serializers

from apps.accounts.models import User
from apps.listings.models import Listing

from apps.payments.models import Payment, PromotionPackage

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


class AdminPaymentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    user_phone = serializers.CharField(source="user.phone", read_only=True)
    listing_title = serializers.CharField(source="listing.title", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "user",
            "user_name",
            "user_phone",
            "listing",
            "listing_title",
            "purpose",
            "amount",
            "currency",
            "payment_method",
            "status",
            "reference",
            "provider_reference",
            "notes",
            "paid_at",
            "created_at",
            "updated_at",
        ]


class AdminMarkPaymentPaidSerializer(serializers.Serializer):
    provider_reference = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255,
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
    )


class AdminMarkPaymentFailedSerializer(serializers.Serializer):
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
    )


class AdminPromotionPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromotionPackage
        fields = [
            "id",
            "name",
            "package_type",
            "description",
            "duration_days",
            "price",
            "currency",
            "is_active",
            "sort_order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]