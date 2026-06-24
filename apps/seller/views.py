from django.db.models import Sum, Count
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsNotBanned, IsVerifiedUser
from apps.listings.models import Listing

from apps.chats.models import ChatThread

from django.utils import timezone

from .serializers import (
    SellerDashboardSummarySerializer,
    SellerListingSerializer,
    SellerAnalyticsSummarySerializer,
    SellerListingAnalyticsSerializer,
)


class SellerDashboardAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBanned,
        IsVerifiedUser,
    ]

    def listing_to_dict(self, listing):
        if not listing:
            return None

        return {
            "id": listing.id,
            "title": listing.title,
            "status": listing.status,
            "price": listing.price,
            "views_count": listing.views_count,
            "favorites_count": listing.favorites_count,
            "is_featured": listing.is_featured,
            "created_at": listing.created_at,
            "expires_at": listing.expires_at,
        }

    def get(self, request):
        listings = Listing.objects.filter(
            seller=request.user,
        ).exclude(
            status=Listing.STATUS_DELETED,
        )

        active_listings = listings.filter(status=Listing.STATUS_ACTIVE)

        total_chat_threads = ChatThread.objects.filter(
            listing__seller=request.user,
        ).count()

        best_listing = (
            listings
            .order_by("-views_count", "-favorites_count", "-created_at")
            .first()
        )

        weakest_listing = (
            active_listings
            .order_by("views_count", "favorites_count", "created_at")
            .first()
        )

        recent_listings = listings.order_by("-created_at")[:5]

        data = {
            "total_listings": listings.count(),
            "active_listings": active_listings.count(),
            "pending_listings": listings.filter(
                status=Listing.STATUS_PENDING,
            ).count(),
            "sold_listings": listings.filter(
                status=Listing.STATUS_SOLD,
            ).count(),
            "expired_listings": listings.filter(
                status=Listing.STATUS_EXPIRED,
            ).count(),
            "unavailable_listings": listings.filter(
                status=Listing.STATUS_UNAVAILABLE,
            ).count(),

            "total_views": listings.aggregate(
                total=Sum("views_count"),
            )["total"] or 0,
            "total_favorites": listings.aggregate(
                total=Sum("favorites_count"),
            )["total"] or 0,
            "total_chat_threads": total_chat_threads,

            "active_featured_listings": active_listings.filter(
                is_featured=True,
                featured_until__gt=timezone.now(),
            ).count(),

            "listings_needing_renewal": listings.filter(
                status=Listing.STATUS_EXPIRED,
            ).count(),

            "best_listing": self.listing_to_dict(best_listing),
            "weakest_listing": self.listing_to_dict(weakest_listing),
            "recent_listings": [
                self.listing_to_dict(listing)
                for listing in recent_listings
            ],
        }

        serializer = SellerDashboardSummarySerializer(data)

        return Response(serializer.data, status=status.HTTP_200_OK)

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
    

class SellerAnalyticsSummaryAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBanned,
        IsVerifiedUser,
    ]

    def get(self, request):
        listings = Listing.objects.filter(seller=request.user)

        total_chat_threads = ChatThread.objects.filter(
            listing__seller=request.user,
        ).count()

        data = {
            "total_listings": listings.exclude(
                status=Listing.STATUS_DELETED,
            ).count(),
            "active_listings": listings.filter(
                status=Listing.STATUS_ACTIVE,
            ).count(),
            "sold_listings": listings.filter(
                status=Listing.STATUS_SOLD,
            ).count(),
            "expired_listings": listings.filter(
                status=Listing.STATUS_EXPIRED,
            ).count(),
            "unavailable_listings": listings.filter(
                status=Listing.STATUS_UNAVAILABLE,
            ).count(),
            "total_views": listings.aggregate(
                total=Sum("views_count"),
            )["total"] or 0,
            "total_favorites": listings.aggregate(
                total=Sum("favorites_count"),
            )["total"] or 0,
            "total_chat_threads": total_chat_threads,
        }

        serializer = SellerAnalyticsSummarySerializer(data)

        return Response(serializer.data, status=status.HTTP_200_OK)


class SellerListingAnalyticsAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBanned,
        IsVerifiedUser,
    ]

    def get(self, request, pk):
        try:
            listing = Listing.objects.get(
                pk=pk,
                seller=request.user,
            )
        except Listing.DoesNotExist:
            return Response(
                {"detail": "Listing not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        chat_threads_count = ChatThread.objects.filter(
            listing=listing,
        ).count()

        data = {
            "listing_id": listing.id,
            "title": listing.title,
            "status": listing.status,
            "price": listing.price,
            "views_count": listing.views_count,
            "favorites_count": listing.favorites_count,
            "chat_threads_count": chat_threads_count,
            "is_featured": listing.is_featured,
            "created_at": listing.created_at,
            "expires_at": listing.expires_at,
        }

        serializer = SellerListingAnalyticsSerializer(data)

        return Response(serializer.data, status=status.HTTP_200_OK)