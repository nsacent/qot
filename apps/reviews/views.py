from django.db.models import Avg, Count
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsNotBanned, IsVerifiedUser
from apps.accounts.models import User

from .models import SellerReview
from .serializers import SellerReviewSerializer, SellerReviewCreateSerializer


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
            .filter(reviewer=self.request.user)
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