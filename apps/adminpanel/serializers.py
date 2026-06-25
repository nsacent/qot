from rest_framework import serializers

from apps.accounts.models import User
from apps.listings.models import Listing
from apps.reviews.models import SellerReview
from apps.chats.models import ChatReport

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
    package_name = serializers.CharField(source="package.name", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "user",
            "user_name",
            "user_phone",
            "listing",
            "listing_title",
            "package",
            "package_name",
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

class AdminDashboardSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    normal_users = serializers.IntegerField()
    admin_users = serializers.IntegerField()
    moderator_users = serializers.IntegerField()
    banned_users = serializers.IntegerField()

    total_listings = serializers.IntegerField()
    active_listings = serializers.IntegerField()
    pending_listings = serializers.IntegerField()
    rejected_listings = serializers.IntegerField()
    sold_listings = serializers.IntegerField()
    expired_listings = serializers.IntegerField()
    unavailable_listings = serializers.IntegerField()

    total_reports = serializers.IntegerField()
    unresolved_reports = serializers.IntegerField()
    resolved_reports = serializers.IntegerField()

    total_payments = serializers.IntegerField()
    pending_payments = serializers.IntegerField()
    paid_payments = serializers.IntegerField()
    failed_payments = serializers.IntegerField()

    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    featured_listing_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    boost_listing_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)

    today_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    this_week_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    this_month_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)

    today_paid_payments = serializers.IntegerField()
    this_week_paid_payments = serializers.IntegerField()
    this_month_paid_payments = serializers.IntegerField()


class AdminCancelPaymentSerializer(serializers.Serializer):
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
    )


class AdminSellerReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source="reviewer.full_name", read_only=True)
    reviewer_phone = serializers.CharField(source="reviewer.phone", read_only=True)
    seller_name = serializers.CharField(source="seller.full_name", read_only=True)
    seller_phone = serializers.CharField(source="seller.phone", read_only=True)
    listing_title = serializers.CharField(source="listing.title", read_only=True)

    class Meta:
        model = SellerReview
        fields = [
            "id",
            "reviewer",
            "reviewer_name",
            "reviewer_phone",
            "seller",
            "seller_name",
            "seller_phone",
            "listing",
            "listing_title",
            "rating",
            "comment",
            "is_visible",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class AdminChatReportSerializer(serializers.ModelSerializer):
    reporter_name = serializers.CharField(source="reporter.full_name", read_only=True)
    reporter_phone = serializers.CharField(source="reporter.phone", read_only=True)
    reported_user_name = serializers.CharField(source="reported_user.full_name", read_only=True)
    reported_user_phone = serializers.CharField(source="reported_user.phone", read_only=True)
    listing_id = serializers.IntegerField(source="thread.listing.id", read_only=True)
    listing_title = serializers.CharField(source="thread.listing.title", read_only=True)

    class Meta:
        model = ChatReport
        fields = [
            "id",
            "thread",
            "listing_id",
            "listing_title",
            "reporter",
            "reporter_name",
            "reporter_phone",
            "reported_user",
            "reported_user_name",
            "reported_user_phone",
            "reason",
            "description",
            "is_resolved",
            "resolved_by",
            "resolved_at",
            "created_at",
        ]
        read_only_fields = fields


class ResolveChatReportSerializer(serializers.Serializer):
    note = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
    )