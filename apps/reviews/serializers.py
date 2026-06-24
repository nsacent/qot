from rest_framework import serializers

from apps.accounts.models import User
from apps.listings.models import Listing

from .models import SellerReview


class SellerReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source="reviewer.full_name", read_only=True)
    seller_name = serializers.CharField(source="seller.full_name", read_only=True)
    listing_title = serializers.CharField(source="listing.title", read_only=True)

    class Meta:
        model = SellerReview
        fields = [
            "id",
            "reviewer",
            "reviewer_name",
            "seller",
            "seller_name",
            "listing",
            "listing_title",
            "rating",
            "comment",
            "is_visible",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "reviewer",
            "reviewer_name",
            "seller_name",
            "listing_title",
            "is_visible",
            "created_at",
            "updated_at",
        ]


class SellerReviewCreateSerializer(serializers.ModelSerializer):
    seller = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True, is_banned=False),
    )
    listing = serializers.PrimaryKeyRelatedField(
        queryset=Listing.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = SellerReview
        fields = [
            "seller",
            "listing",
            "rating",
            "comment",
        ]

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")

        return value

    def validate(self, attrs):
        request = self.context["request"]
        reviewer = request.user
        seller = attrs["seller"]
        listing = attrs.get("listing")

        if seller == reviewer:
            raise serializers.ValidationError(
                {"seller": "You cannot review yourself."}
            )

        if listing and listing.seller != seller:
            raise serializers.ValidationError(
                {"listing": "This listing does not belong to the selected seller."}
            )

        existing_review = SellerReview.objects.filter(
            reviewer=reviewer,
            seller=seller,
            listing=listing,
        ).exists()

        if existing_review:
            raise serializers.ValidationError(
                "You have already reviewed this seller for this listing."
            )

        return attrs

    def create(self, validated_data):
        request = self.context["request"]

        return SellerReview.objects.create(
            reviewer=request.user,
            **validated_data,
        )