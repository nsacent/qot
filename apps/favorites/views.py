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

    @transaction.atomic
    def post(self, request, listing_id):
        try:
            listing = Listing.objects.get(
                pk=listing_id,
                status=Listing.STATUS_ACTIVE,
            )
        except Listing.DoesNotExist:
            return Response(
                {
                    "detail": "Active listing not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        favorite, created = Favorite.objects.get_or_create(
            user=request.user,
            listing=listing,
        )

        if not created:
            return Response(
                {
                    "message": "Listing is already saved."
                },
                status=status.HTTP_200_OK,
            )

        Listing.objects.filter(pk=listing.pk).update(
            favorites_count=F("favorites_count") + 1
        )

        return Response(
            {
                "message": "Listing saved successfully."
            },
            status=status.HTTP_201_CREATED,
        )

    @transaction.atomic
    def delete(self, request, listing_id):
        deleted_count, _ = Favorite.objects.filter(
            user=request.user,
            listing_id=listing_id,
        ).delete()

        if deleted_count == 0:
            return Response(
                {
                    "detail": "Saved listing not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        Listing.objects.filter(
            pk=listing_id,
            favorites_count__gt=0,
        ).update(
            favorites_count=F("favorites_count") - 1
        )

        return Response(
            {
                "message": "Listing removed from saved ads."
            },
            status=status.HTTP_200_OK,
        )