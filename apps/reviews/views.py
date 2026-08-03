from django.db.models import Avg, Count
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsNotBanned, IsVerifiedUser
from apps.accounts.models import User
from apps.listings.models import Listing

from .models import SellerReview
from .serializers import SellerReviewSerializer, SellerReviewCreateSerializer
from .eligibility import accepted_offer_queryset, get_reviewable_offer


class SellerReviewCreateAPIView(generics.CreateAPIView):
    serializer_class = SellerReviewCreateSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBanned,
        IsVerifiedUser,
    ]


class SellerReviewListAPIView(generics.ListAPIView):
    serializer_class = SellerReviewSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        seller_id = self.kwargs["seller_id"]

        return (
            SellerReview.objects
            .filter(
                seller_id=seller_id,
                is_visible=True,
                is_verified_transaction=True,
            )
            .select_related("reviewer", "seller", "listing")
            .order_by("-created_at")
        )


class MyGivenReviewsAPIView(generics.ListAPIView):
    serializer_class = SellerReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            SellerReview.objects
            .filter(
                reviewer=self.request.user,
                is_verified_transaction=True,
            )
            .select_related("reviewer", "seller", "listing")
            .order_by("-created_at")
        )


class SellerReviewSummaryAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, seller_id):
        try:
            seller = User.objects.get(
                id=seller_id,
                is_active=True,
                is_banned=False,
            )
        except User.DoesNotExist:
            return Response(
                {"detail": "Seller not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        summary = SellerReview.objects.filter(
            seller=seller,
            is_visible=True,
            is_verified_transaction=True,
        ).aggregate(
            average_rating=Avg("rating"),
            total_reviews=Count("id"),
        )

        data = {
            "seller": seller.id,
            "seller_name": seller.full_name,
            "average_rating": round(summary["average_rating"] or 0, 1),
            "total_reviews": summary["total_reviews"] or 0,
        }

        return Response(data, status=status.HTTP_200_OK)


def transaction_payload(request, offer):
    listing = offer.thread.listing
    primary_image = (
        listing.images
        .order_by("-is_primary", "sort_order", "id")
        .first()
    )
    image_url = ""
    if primary_image:
        image_field = (
            primary_image.card_image
            or primary_image.image
        )
        if image_field:
            image_url = request.build_absolute_uri(image_field.url)

    return {
        "listing": listing.id,
        "listing_title": listing.title,
        "listing_image": image_url,
        "seller": listing.seller_id,
        "seller_name": listing.seller.full_name,
        "offer": offer.id,
        "offer_amount": offer.offer_amount,
        "completed_at": listing.sold_at,
    }


class TransactionReviewEligibilityAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsNotBanned]

    def get(self, request):
        listing_id = request.query_params.get("listing")
        if not listing_id:
            return Response(
                {"detail": "Choose an ad to check review eligibility."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            listing = Listing.objects.select_related("seller").get(pk=listing_id)
        except (Listing.DoesNotExist, TypeError, ValueError):
            return Response(
                {"detail": "Ad not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        existing_review = SellerReview.objects.filter(
            reviewer=request.user,
            listing=listing,
            is_verified_transaction=True,
        ).first()
        if existing_review:
            return Response(
                {
                    "eligible": False,
                    "already_reviewed": True,
                    "review_id": existing_review.id,
                    "reason": "You have already reviewed this transaction.",
                }
            )

        offer = get_reviewable_offer(request.user, listing)
        if offer:
            return Response(
                {
                    "eligible": True,
                    "already_reviewed": False,
                    "transaction": transaction_payload(request, offer),
                }
            )

        reason = (
            "This review will unlock after the seller marks the ad as sold."
            if accepted_offer_queryset(request.user, listing).exists()
            else "Only the buyer whose offer was accepted can review this transaction."
        )
        return Response(
            {
                "eligible": False,
                "already_reviewed": False,
                "reason": reason,
            }
        )


class EligibleTransactionReviewListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsNotBanned]

    def get(self, request):
        reviewed_listing_ids = set(
            SellerReview.objects
            .filter(
                reviewer=request.user,
                is_verified_transaction=True,
            )
            .values_list("listing_id", flat=True)
        )
        results = []
        seen_listing_ids = set()
        offers = accepted_offer_queryset(request.user).filter(
            thread__listing__status=Listing.STATUS_SOLD,
            thread__listing__sold_at__isnull=False,
        )

        for offer in offers:
            listing_id = offer.thread.listing_id
            if listing_id in reviewed_listing_ids or listing_id in seen_listing_ids:
                continue

            results.append(transaction_payload(request, offer))
            seen_listing_ids.add(listing_id)
            if len(results) >= 50:
                break

        return Response({"count": len(results), "results": results})
