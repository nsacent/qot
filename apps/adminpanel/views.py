from django.db.models import Count
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.listings.models import Listing
from apps.moderation.models import ListingReport
from apps.accounts.trust import calculate_user_trust_score

from datetime import timedelta
from django.utils import timezone

from .permissions import IsAdminOrModerator

from apps.payments.models import Payment, PromotionPackage

from .serializers import (
    AdminUserSerializer,
    AdminListingSerializer,
    ListingRejectSerializer,
    UserBanSerializer,
    FeatureListingSerializer,
    AdminPaymentSerializer,
    AdminMarkPaymentPaidSerializer,
    AdminMarkPaymentFailedSerializer,
    AdminPromotionPackageSerializer
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

class FeatureListingAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrModerator]

    def post(self, request, pk):
        try:
            listing = Listing.objects.get(pk=pk)
        except Listing.DoesNotExist:
            return Response(
                {"detail": "Listing not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = FeatureListingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        days = serializer.validated_data["days"]

        listing.is_featured = True
        listing.featured_until = timezone.now() + timedelta(days=days)
        listing.save(update_fields=["is_featured", "featured_until", "updated_at"])

        return Response(
            {
                "message": "Listing featured successfully.",
                "listing": AdminListingSerializer(listing).data,
            },
            status=status.HTTP_200_OK,
        )


class UnfeatureListingAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrModerator]

    def post(self, request, pk):
        try:
            listing = Listing.objects.get(pk=pk)
        except Listing.DoesNotExist:
            return Response(
                {"detail": "Listing not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        listing.is_featured = False
        listing.featured_until = None
        listing.save(update_fields=["is_featured", "featured_until", "updated_at"])

        return Response(
            {
                "message": "Listing unfeatured successfully.",
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

class AdminPaymentListAPIView(generics.ListAPIView):
    serializer_class = AdminPaymentSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsAdminOrModerator,
    ]

    def get_queryset(self):
        queryset = (
            Payment.objects
            .select_related("user", "listing")
            .order_by("-created_at")
        )

        status_param = self.request.query_params.get("status")
        purpose = self.request.query_params.get("purpose")

        if status_param:
            queryset = queryset.filter(status=status_param)

        if purpose:
            queryset = queryset.filter(purpose=purpose)

        return queryset


class AdminMarkPaymentPaidAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsAdminOrModerator,
    ]

    def post(self, request, pk):
        try:
            payment = Payment.objects.select_related("listing", "package").get(pk=pk)
        except Payment.DoesNotExist:
            return Response(
                {"detail": "Payment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AdminMarkPaymentPaidSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment.status = Payment.STATUS_PAID
        payment.provider_reference = serializer.validated_data.get(
            "provider_reference",
            "",
        )
        payment.notes = serializer.validated_data.get("notes", "")
        payment.paid_at = timezone.now()
        payment.save(
            update_fields=[
                "status",
                "provider_reference",
                "notes",
                "paid_at",
                "updated_at",
            ]
        )

        if (
            payment.purpose == Payment.PURPOSE_FEATURED_LISTING
            and payment.listing is not None
        ):
            payment.listing.is_featured = True

            duration_days = 7

            if payment.package:
                duration_days = payment.package.duration_days

            payment.listing.featured_until = timezone.now() + timedelta(days=duration_days)

            payment.listing.save(
                update_fields=[
                    "is_featured",
                    "featured_until",
                    "updated_at",
                ]
            )

        return Response(
            {
                "message": "Payment marked as paid successfully.",
                "payment": AdminPaymentSerializer(payment).data,
            },
            status=status.HTTP_200_OK,
        )


class AdminMarkPaymentFailedAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsAdminOrModerator,
    ]

    def post(self, request, pk):
        try:
            payment = Payment.objects.get(pk=pk)
        except Payment.DoesNotExist:
            return Response(
                {"detail": "Payment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AdminMarkPaymentFailedSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment.status = Payment.STATUS_FAILED
        payment.notes = serializer.validated_data.get("notes", "")
        payment.save(update_fields=["status", "notes", "updated_at"])

        return Response(
            {
                "message": "Payment marked as failed.",
                "payment": AdminPaymentSerializer(payment).data,
            },
            status=status.HTTP_200_OK,
        )
    

class AdminPromotionPackageListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = AdminPromotionPackageSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsAdminOrModerator,
    ]

    def get_queryset(self):
        queryset = PromotionPackage.objects.all().order_by(
            "sort_order",
            "price",
            "name",
        )

        package_type = self.request.query_params.get("package_type")
        is_active = self.request.query_params.get("is_active")

        if package_type:
            queryset = queryset.filter(package_type=package_type)

        if is_active == "true":
            queryset = queryset.filter(is_active=True)

        if is_active == "false":
            queryset = queryset.filter(is_active=False)

        return queryset


class AdminPromotionPackageDetailAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = AdminPromotionPackageSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsAdminOrModerator,
    ]

    queryset = PromotionPackage.objects.all()