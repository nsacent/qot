from django.db import transaction
from django.db.models import F

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.listings.models import Listing

from .models import Favorite
from .serializers import FavoriteSerializer

from apps.common.permissions import IsNotBanned, IsVerifiedUser

class FavoriteListAPIView(generics.ListAPIView):
    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Favorite.objects
            .filter(user=self.request.user)
            .select_related(
                "listing",
                "listing__seller",
                "listing__category",
                "listing__category__parent",
                "listing__city",
            )
            .prefetch_related("listing__images")
            .order_by("-created_at")
        )


class FavoriteToggleAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBanned,
        IsVerifiedUser,
    ]

    def post(self, request, listing_id):
        try:
            listing = Listing.objects.get(
                pk=listing_id,
                status=Listing.STATUS_ACTIVE,
            )
        except Listing.DoesNotExist:
            return Response(
                {"detail": "Listing not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        favorite, created = Favorite.objects.get_or_create(
            user=request.user,
            listing=listing,
        )

        if created:
            Listing.objects.filter(pk=listing.pk).update(
                favorites_count=F("favorites_count") + 1
            )

            listing.refresh_from_db(fields=["favorites_count"])

            return Response(
                {
                    "message": "Listing added to favorites.",
                    "is_favorited": True,
                    "favorites_count": listing.favorites_count,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {
                "message": "Listing is already in favorites.",
                "is_favorited": True,
                "favorites_count": listing.favorites_count,
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request, listing_id):
        try:
            listing = Listing.objects.get(pk=listing_id)
        except Listing.DoesNotExist:
            return Response(
                {"detail": "Listing not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        deleted_count, _ = Favorite.objects.filter(
            user=request.user,
            listing=listing,
        ).delete()

        if deleted_count:
            Listing.objects.filter(
                pk=listing.pk,
                favorites_count__gt=0,
            ).update(
                favorites_count=F("favorites_count") - 1
            )

            listing.refresh_from_db(fields=["favorites_count"])

            return Response(
                {
                    "message": "Listing removed from favorites.",
                    "is_favorited": False,
                    "favorites_count": listing.favorites_count,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "message": "Listing was not in favorites.",
                "is_favorited": False,
                "favorites_count": listing.favorites_count,
            },
            status=status.HTTP_200_OK,
        )
