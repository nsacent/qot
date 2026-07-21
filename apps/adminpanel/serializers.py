from django.db import transaction
from django.db.models import Avg, Count, Sum
from rest_framework import serializers

from apps.accounts.models import User
from apps.listings.models import Listing
from apps.listings.serializers import (
    ListingCreateUpdateSerializer,
    ListingAttributeSerializer,
    ListingImageSerializer,
)
from apps.moderation.models import ListingReport
from apps.reviews.models import SellerReview

from apps.payments.models import Payment, PromotionPackage

from apps.chats.models import ChatReport, ChatBlock

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


class AdminUserDetailSerializer(AdminUserSerializer):
    avatar_url = serializers.SerializerMethodField()
    business_name = serializers.CharField(
        source="profile.business_name",
        read_only=True,
        default="",
    )
    bio = serializers.CharField(
        source="profile.bio",
        read_only=True,
        default="",
    )
    trust_score = serializers.IntegerField(
        source="profile.trust_score",
        read_only=True,
        default=0,
    )
    google_connected = serializers.SerializerMethodField()
    listing_counts = serializers.SerializerMethodField()
    stats = serializers.SerializerMethodField()
    recent_listings = serializers.SerializerMethodField()
    recent_payments = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta(AdminUserSerializer.Meta):
        fields = AdminUserSerializer.Meta.fields + [
            "last_login",
            "updated_at",
            "avatar_url",
            "business_name",
            "bio",
            "trust_score",
            "google_connected",
            "listing_counts",
            "stats",
            "recent_listings",
            "recent_payments",
            "permissions",
        ]
        read_only_fields = fields

    def get_avatar_url(self, obj):
        profile = getattr(obj, "profile", None)

        if not profile or not profile.avatar:
            return None

        request = self.context.get("request")

        if request:
            return request.build_absolute_uri(profile.avatar.url)

        return profile.avatar.url

    def get_google_connected(self, obj):
        return bool(obj.google_sub)

    def get_listing_counts(self, obj):
        counts = obj.listings.values("status").annotate(total=Count("id"))
        return {row["status"]: row["total"] for row in counts}

    def get_stats(self, obj):
        paid_payments = obj.payments.filter(status=Payment.STATUS_PAID)
        paid_spend = paid_payments.aggregate(total=Sum("amount"))["total"] or 0
        review_summary = obj.received_reviews.filter(is_visible=True).aggregate(
            total=Count("id"),
            average=Avg("rating"),
        )

        return {
            "listings": obj.listings.exclude(status=Listing.STATUS_DELETED).count(),
            "favorites": obj.favorites.count(),
            "payments": obj.payments.count(),
            "paid_spend": str(paid_spend),
            "reviews": review_summary["total"] or 0,
            "average_rating": review_summary["average"],
            "reports_submitted": obj.listing_reports.count(),
            "reports_against": ListingReport.objects.filter(
                listing__seller=obj
            ).count(),
        }

    def get_recent_listings(self, obj):
        listings = (
            obj.listings
            .exclude(status=Listing.STATUS_DELETED)
            .select_related("seller", "category", "city")
            .prefetch_related("images")
            .order_by("-created_at")[:6]
        )
        return AdminListingSerializer(
            listings,
            many=True,
            context=self.context,
        ).data

    def get_recent_payments(self, obj):
        payments = (
            obj.payments
            .select_related("user", "listing", "package")
            .order_by("-created_at")[:6]
        )
        return AdminPaymentSerializer(
            payments,
            many=True,
            context=self.context,
        ).data

    def get_permissions(self, obj):
        request = self.context.get("request")
        requester = getattr(request, "user", None)
        requester_is_superuser = bool(
            requester
            and requester.is_authenticated
            and requester.is_superuser
        )
        is_admin = bool(
            requester
            and requester.is_authenticated
            and (
                requester_is_superuser
                or requester.role == User.ROLE_ADMIN
            )
        )
        is_staff_target = obj.role in {
            User.ROLE_ADMIN,
            User.ROLE_MODERATOR,
        }

        return {
            "is_self": bool(requester and requester.pk == obj.pk),
            "can_edit": is_admin and (not obj.is_superuser or requester_is_superuser),
            "can_manage_role": (
                is_admin and not obj.is_superuser
            ),
            "can_manage_access": (
                (is_admin or not is_staff_target)
                and (not obj.is_superuser or requester_is_superuser)
            ),
        }


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "full_name",
            "phone",
            "email",
            "role",
            "is_active",
            "is_verified",
        ]
        extra_kwargs = {
            "phone": {"allow_null": True, "allow_blank": True, "required": False},
            "email": {"allow_null": True, "allow_blank": True, "required": False},
        }

    def validate_full_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Full name cannot be empty.")

        return value

    def validate_phone(self, value):
        value = value.strip() if value else None

        if value and User.objects.filter(phone=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("This phone number is already in use.")

        return value

    def validate_email(self, value):
        value = value.strip().lower() if value else None

        if value and User.objects.filter(email__iexact=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("This email address is already in use.")

        return value

    def validate(self, attrs):
        request = self.context["request"]
        target = self.instance
        final_phone = attrs.get("phone", target.phone)
        final_email = attrs.get("email", target.email)
        final_role = attrs.get("role", target.role)
        final_is_active = attrs.get("is_active", target.is_active)

        if not final_phone and not final_email:
            raise serializers.ValidationError(
                "An account must have at least a phone number or email address."
            )

        if request.user.pk == target.pk:
            if final_role != target.role:
                raise serializers.ValidationError(
                    {"role": "You cannot change your own administrator role."}
                )

            if not final_is_active:
                raise serializers.ValidationError(
                    {"is_active": "You cannot deactivate your own account."}
                )

        if target.is_superuser and final_role != User.ROLE_ADMIN:
            raise serializers.ValidationError(
                {"role": "A superuser must retain the administrator role."}
            )

        removing_active_admin = (
            target.role == User.ROLE_ADMIN
            and target.is_active
            and not target.is_banned
            and (
                final_role != User.ROLE_ADMIN
                or not final_is_active
            )
        )

        if removing_active_admin:
            active_admins = User.objects.filter(
                role=User.ROLE_ADMIN,
                is_active=True,
                is_banned=False,
            ).count()

            if active_admins <= 1:
                raise serializers.ValidationError(
                    "The platform must retain at least one active administrator."
                )

        return attrs

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        should_be_staff = instance.is_superuser or instance.role in {
            User.ROLE_ADMIN,
            User.ROLE_MODERATOR,
        }

        if instance.is_staff != should_be_staff:
            instance.is_staff = should_be_staff
            instance.save(update_fields=["is_staff", "updated_at"])

        return instance


class AdminListingSerializer(serializers.ModelSerializer):
    seller_name = serializers.CharField(source="seller.full_name", read_only=True)
    seller_phone = serializers.CharField(source="seller.phone", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    primary_image = serializers.SerializerMethodField()

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
            "primary_image",
            "created_at",
            "updated_at",
        ]

    def get_primary_image(self, obj):
        image = obj.images.filter(is_primary=True).first() or obj.images.first()

        if not image or not image.image:
            return None

        request = self.context.get("request")

        if request:
            return request.build_absolute_uri(image.image.url)

        return image.image.url


class AdminListingDetailSerializer(AdminListingSerializer):
    seller_email = serializers.EmailField(source="seller.email", read_only=True)
    seller_role = serializers.CharField(source="seller.role", read_only=True)
    seller_is_active = serializers.BooleanField(
        source="seller.is_active",
        read_only=True,
    )
    seller_is_verified = serializers.BooleanField(
        source="seller.is_verified",
        read_only=True,
    )
    seller_is_banned = serializers.BooleanField(
        source="seller.is_banned",
        read_only=True,
    )
    category_parent_name = serializers.SerializerMethodField()
    region_name = serializers.CharField(source="city.region.name", read_only=True)
    images = ListingImageSerializer(many=True, read_only=True)
    attributes = ListingAttributeSerializer(many=True, read_only=True)
    image_count = serializers.SerializerMethodField()
    reports_count = serializers.SerializerMethodField()
    open_reports_count = serializers.SerializerMethodField()

    class Meta(AdminListingSerializer.Meta):
        fields = AdminListingSerializer.Meta.fields + [
            "seller_email",
            "seller_role",
            "seller_is_active",
            "seller_is_verified",
            "seller_is_banned",
            "category_parent_name",
            "region_name",
            "description",
            "is_negotiable",
            "expires_at",
            "sold_at",
            "images",
            "image_count",
            "attributes",
            "reports_count",
            "open_reports_count",
        ]
        read_only_fields = fields

    def get_category_parent_name(self, obj):
        parent = getattr(obj.category, "parent", None)
        return parent.name if parent else None

    def get_image_count(self, obj):
        return obj.images.count()

    def get_reports_count(self, obj):
        return obj.reports.count()

    def get_open_reports_count(self, obj):
        return obj.reports.filter(is_resolved=False).count()


class AdminListingUpdateSerializer(ListingCreateUpdateSerializer):
    """Edit listing content without changing its moderation lifecycle."""

    @transaction.atomic
    def update(self, instance, validated_data):
        attributes_data = validated_data.pop("attributes", None)
        updated_fields = []

        for attribute, value in validated_data.items():
            setattr(instance, attribute, value)
            updated_fields.append(attribute)

        if updated_fields:
            instance.save(update_fields=[*updated_fields, "updated_at"])

        if attributes_data is not None:
            instance.attributes.all().delete()
            self._save_attributes(instance, attributes_data)

        return instance


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


class AdminChatBlockSerializer(serializers.ModelSerializer):
    blocker_name = serializers.CharField(source="blocker.full_name", read_only=True)
    blocker_phone = serializers.CharField(source="blocker.phone", read_only=True)

    blocked_user_name = serializers.CharField(source="blocked_user.full_name", read_only=True)
    blocked_user_phone = serializers.CharField(source="blocked_user.phone", read_only=True)

    listing_id = serializers.IntegerField(source="thread.listing.id", read_only=True)
    listing_title = serializers.CharField(source="thread.listing.title", read_only=True)

    class Meta:
        model = ChatBlock
        fields = [
            "id",
            "blocker",
            "blocker_name",
            "blocker_phone",
            "blocked_user",
            "blocked_user_name",
            "blocked_user_phone",
            "thread",
            "listing_id",
            "listing_title",
            "reason",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
