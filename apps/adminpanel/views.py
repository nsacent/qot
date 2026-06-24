from django.db.models import Count
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.listings.models import Listing
from apps.moderation.models import ListingReport
from apps.accounts.trust import calculate_user_trust_score

from .permissions import IsAdminOrModerator
from .serializers import (
    AdminUserSerializer,
    AdminListingSerializer,
    ListingRejectSerializer,
    UserBanSerializer,
)

from apps.notifications.services import (
    create_listing_approved_notification,
    create_listing_rejected_notification,
)

class AdminDashboardAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrModerator]

    def get(self, request):
        data = {
            "users": {
                "total": User.objects.count(),
                "active": User.objects.filter(is_active=True, is_banned=False).count(),
                "banned": User.objects.filter(is_banned=True).count(),
                "verified": User.objects.filter(is_verified=True).count(),
            },
            "listings": {
                "total": Listing.objects.exclude(status=Listing.STATUS_DELETED).count(),
                "pending": Listing.objects.filter(status=Listing.STATUS_PENDING).count(),
                "active": Listing.objects.filter(status=Listing.STATUS_ACTIVE).count(),
                "rejected": Listing.objects.filter(status=Listing.STATUS_REJECTED).count(),
                "sold": Listing.objects.filter(status=Listing.STATUS_SOLD).count(),
                "expired": Listing.objects.filter(status=Listing.STATUS_EXPIRED).count(),
            },
            "reports": {
                "total": ListingReport.objects.count(),
                "open": ListingReport.objects.filter(is_resolved=False).count(),
                "resolved": ListingReport.objects.filter(is_resolved=True).count(),
            },
            "top_categories": list(
                Listing.objects
                .exclude(status=Listing.STATUS_DELETED)
                .values("category__name")
                .annotate(total=Count("id"))
                .order_by("-total")[:10]
            ),
        }

        return Response(data, status=status.HTTP_200_OK)


class PendingListingListAPIView(generics.ListAPIView):
    serializer_class = AdminListingSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrModerator]

    def get_queryset(self):
        return (
            Listing.objects
            .filter(status=Listing.STATUS_PENDING)
            .select_related("seller", "category", "city")
            .order_by("-created_at")
        )


class AdminListingListAPIView(generics.ListAPIView):
    serializer_class = AdminListingSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrModerator]

    def get_queryset(self):
        queryset = (
            Listing.objects
            .exclude(status=Listing.STATUS_DELETED)
            .select_related("seller", "category", "city")
            .order_by("-created_at")
        )

        status_param = self.request.query_params.get("status")

        if status_param:
            queryset = queryset.filter(status=status_param)

        return queryset


class ApproveListingAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrModerator]

    def post(self, request, pk):
        try:
            listing = Listing.objects.get(pk=pk)
        except Listing.DoesNotExist:
            return Response(
                {"detail": "Listing not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        listing.status = Listing.STATUS_ACTIVE
        listing.rejection_reason = ""
        listing.save(update_fields=["status", "rejection_reason", "updated_at"])

        create_listing_approved_notification(listing)
        calculate_user_trust_score(listing.seller)

        return Response(
            {
                "message": "Listing approved successfully.",
                "listing": AdminListingSerializer(listing).data,
            },
            status=status.HTTP_200_OK,
        )


class RejectListingAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrModerator]

    def post(self, request, pk):
        try:
            listing = Listing.objects.get(pk=pk)
        except Listing.DoesNotExist:
            return Response(
                {"detail": "Listing not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ListingRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        listing.status = Listing.STATUS_REJECTED
        listing.rejection_reason = serializer.validated_data["rejection_reason"]
        listing.save(update_fields=["status", "rejection_reason", "updated_at"])

        create_listing_rejected_notification(listing)
        calculate_user_trust_score(listing.seller)

        return Response(
            {
                "message": "Listing rejected successfully.",
                "listing": AdminListingSerializer(listing).data,
            },
            status=status.HTTP_200_OK,
        )


class AdminUserListAPIView(generics.ListAPIView):
    serializer_class = AdminUserSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrModerator]

    def get_queryset(self):
        queryset = User.objects.all().order_by("-date_joined")

        role = self.request.query_params.get("role")
        is_banned = self.request.query_params.get("is_banned")

        if role:
            queryset = queryset.filter(role=role)

        if is_banned == "true":
            queryset = queryset.filter(is_banned=True)

        if is_banned == "false":
            queryset = queryset.filter(is_banned=False)

        return queryset


class BanUserAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrModerator]

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if user == request.user:
            return Response(
                {"detail": "You cannot ban your own account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = UserBanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user.is_banned = True
        user.banned_reason = serializer.validated_data.get("banned_reason", "")
        user.save(update_fields=["is_banned", "banned_reason", "updated_at"])
        calculate_user_trust_score(user)

        return Response(
            {
                "message": "User banned successfully.",
                "user": AdminUserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class UnbanUserAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrModerator]

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        user.is_banned = False
        user.banned_reason = ""
        user.save(update_fields=["is_banned", "banned_reason", "updated_at"])

        return Response(
            {
                "message": "User unbanned successfully.",
                "user": AdminUserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )