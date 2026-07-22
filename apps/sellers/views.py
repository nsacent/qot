from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User, UserFollow
from apps.listings.models import Listing

from .serializers import (
    PublicSellerSerializer,
    PublicSellerListingSerializer,
    SellerFollowUserSerializer,
)


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


class SellerFollowAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_seller(self, seller_id):
        return get_object_or_404(
            User.objects.select_related("profile"),
            pk=seller_id,
            is_active=True,
            is_banned=False,
        )

    def post(self, request, seller_id):
        seller = self.get_seller(seller_id)

        if seller == request.user:
            return Response(
                {"detail": "You cannot follow your own profile."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        _, created = UserFollow.objects.get_or_create(
            follower=request.user,
            following=seller,
        )

        return Response(
            {
                "is_following": True,
                "created": created,
                "followers_count": seller.follower_relationships.count(),
                "following_count": seller.following_relationships.count(),
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request, seller_id):
        seller = self.get_seller(seller_id)
        UserFollow.objects.filter(
            follower=request.user,
            following=seller,
        ).delete()

        return Response(
            {
                "is_following": False,
                "followers_count": seller.follower_relationships.count(),
                "following_count": seller.following_relationships.count(),
            },
            status=status.HTTP_200_OK,
        )


class SellerFollowersAPIView(generics.ListAPIView):
    serializer_class = SellerFollowUserSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        seller = get_object_or_404(
            User,
            pk=self.kwargs["seller_id"],
            is_active=True,
            is_banned=False,
        )
        return (
            User.objects.filter(
                following_relationships__following=seller,
                is_active=True,
                is_banned=False,
            )
            .select_related("profile")
            .order_by("-following_relationships__created_at")
        )


class SellerFollowingAPIView(generics.ListAPIView):
    serializer_class = SellerFollowUserSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        seller = get_object_or_404(
            User,
            pk=self.kwargs["seller_id"],
            is_active=True,
            is_banned=False,
        )
        return (
            User.objects.filter(
                follower_relationships__follower=seller,
                is_active=True,
                is_banned=False,
            )
            .select_related("profile")
            .order_by("-follower_relationships__created_at")
        )
