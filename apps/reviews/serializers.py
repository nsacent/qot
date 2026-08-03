from rest_framework import serializers

from apps.accounts.models import User
from apps.listings.models import Listing

from .models import SellerReview
from .eligibility import get_reviewable_offer

from apps.accounts.trust import calculate_user_trust_score
from apps.notifications.services import create_review_notification


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
            "item_accuracy_rating",
            "item_condition_rating",
            "communication_rating",
            "comment",
            "is_visible",
            "is_verified_transaction",
            "verified_offer",
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
            "is_verified_transaction",
            "verified_offer",
            "created_at",
            "updated_at",
        ]


class SellerReviewCreateSerializer(serializers.ModelSerializer):
    seller = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True, is_banned=False),
    )
    listing = serializers.PrimaryKeyRelatedField(
        queryset=Listing.objects.all(),
        required=True,
    )
    item_accuracy_rating = serializers.IntegerField(
        min_value=1,
        max_value=5,
        required=False,
    )
    item_condition_rating = serializers.IntegerField(
        min_value=1,
        max_value=5,
        required=False,
    )
    communication_rating = serializers.IntegerField(
        min_value=1,
        max_value=5,
        required=False,
    )
    comment = serializers.CharField(min_length=5, max_length=1000)

    class Meta:
        model = SellerReview
        fields = [
            "seller",
            "listing",
            "rating",
            "item_accuracy_rating",
            "item_condition_rating",
            "communication_rating",
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

        verified_offer = get_reviewable_offer(reviewer, listing)
        if verified_offer is None:
            if listing.status != Listing.STATUS_SOLD or not listing.sold_at:
                raise serializers.ValidationError(
                    {
                        "listing": (
                            "This transaction can be reviewed after the seller "
                            "marks the ad as sold."
                        )
                    }
                )

            raise serializers.ValidationError(
                {
                    "listing": (
                        "Only the buyer whose offer was accepted can review "
                        "this transaction."
                    )
                }
            )

        for field in (
            "item_accuracy_rating",
            "item_condition_rating",
            "communication_rating",
        ):
            attrs.setdefault(field, attrs["rating"])

        attrs["is_verified_transaction"] = True
        attrs["verified_offer"] = verified_offer

        return attrs

    def create(self, validated_data):
        request = self.context["request"]

        review = SellerReview.objects.create(
            reviewer=request.user,
            **validated_data,
        )

        calculate_user_trust_score(review.seller)
        create_review_notification(review)

        return review
