from django.db.models import Sum
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsNotBanned, IsVerifiedUser
from apps.listings.models import Listing

from .serializers import SellerListingSerializer


class SellerDashboardAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBanned,
        IsVerifiedUser,
    ]

    def get(self, request):
        listings = Listing.objects.filter(
            seller=request.user,
        ).exclude(
            status=Listing.STATUS_DELETED,
        )

        data = {
            "listings": {
                "total": listings.count(),
                "active": listings.filter(status=Listing.STATUS_ACTIVE).count(),
                "pending": listings.filter(status=Listing.STATUS_PENDING).count(),
                "rejected": listings.filter(status=Listing.STATUS_REJECTED).count(),
                "sold": listings.filter(status=Listing.STATUS_SOLD).count(),
                "expired": listings.filter(status=Listing.STATUS_EXPIRED).count(),
                "draft": listings.filter(status=Listing.STATUS_DRAFT).count(),
            },
            "performance": {
                "total_views": listings.aggregate(total=Sum("views_count"))["total"] or 0,
                "total_favorites": listings.aggregate(total=Sum("favorites_count"))["total"] or 0,
            },
        }

        return Response(data, status=status.HTTP_200_OK)


class SellerListingListAPIView(generics.ListAPIView):
    serializer_class = SellerListingSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBanned,
        IsVerifiedUser,
    ]

    def get_queryset(self):
        queryset = (
            Listing.objects
            .filter(seller=self.request.user)
            .exclude(status=Listing.STATUS_DELETED)
            .select_related("category", "city")
            .prefetch_related("images")
            .order_by("-created_at")
        )

        status_param = self.request.query_params.get("status")

        if status_param:
            queryset = queryset.filter(status=status_param)

        return queryset