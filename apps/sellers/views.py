from rest_framework import generics, permissions

from apps.accounts.models import User
from apps.listings.models import Listing

from .serializers import PublicSellerSerializer, PublicSellerListingSerializer


class PublicSellerDetailAPIView(generics.RetrieveAPIView):
    serializer_class = PublicSellerSerializer
    permission_classes = [permissions.AllowAny]
    lookup_url_kwarg = "seller_id"

    def get_queryset(self):
        return (
            User.objects
            .filter(is_active=True, is_banned=False)
            .select_related("profile")
        )


class PublicSellerListingListAPIView(generics.ListAPIView):
    serializer_class = PublicSellerListingSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        seller_id = self.kwargs["seller_id"]

        return (
            Listing.objects
            .filter(
                seller_id=seller_id,
                seller__is_active=True,
                seller__is_banned=False,
                status=Listing.STATUS_ACTIVE,
            )
            .select_related("seller", "category", "city")
            .prefetch_related("images")
            .order_by("-is_featured", "-created_at")
        )