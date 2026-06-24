from django.db.models import Count, Sum
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
    AdminPromotionPackageSerializer,
    AdminDashboardSerializer,
)

from apps.notifications.services import (
    create_listing_approved_notification,
    create_listing_rejected_notification,
    create_payment_paid_notification,
    create_payment_failed_notification,
)

class AdminDashboardAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsAdminOrModerator,
    ]

    def get(self, request):
        users = User.objects.all()
        listings = Listing.objects.exclude(status=Listing.STATUS_DELETED)
        reports = ListingReport.objects.all()
        payments = Payment.objects.all()

        paid_payments = payments.filter(status=Payment.STATUS_PAID)

        now = timezone.now()
        today = now.date()
        week_start = today - timezone.timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        today_paid = paid_payments.filter(
            paid_at__date=today,
        )

        this_week_paid = paid_payments.filter(
            paid_at__date__gte=week_start,
        )

        this_month_paid = paid_payments.filter(
            paid_at__date__gte=month_start,
        )

        total_revenue = paid_payments.aggregate(
            total=Sum("amount"),
        )["total"] or 0

        featured_listing_revenue = paid_payments.filter(
            purpose=Payment.PURPOSE_FEATURED_LISTING,
        ).aggregate(
            total=Sum("amount"),
        )["total"] or 0

        boost_listing_revenue = paid_payments.filter(
            purpose=Payment.PURPOSE_BOOST_LISTING,
        ).aggregate(
            total=Sum("amount"),
        )["total"] or 0

        today_revenue = today_paid.aggregate(
            total=Sum("amount"),
        )["total"] or 0

        this_week_revenue = this_week_paid.aggregate(
            total=Sum("amount"),
        )["total"] or 0

        this_month_revenue = this_month_paid.aggregate(
            total=Sum("amount"),
        )["total"] or 0

        data = {
            "total_users": users.count(),
            "normal_users": users.filter(role=User.ROLE_USER).count(),
            "admin_users": users.filter(role=User.ROLE_ADMIN).count(),
            "moderator_users": users.filter(role=User.ROLE_MODERATOR).count(),
            "banned_users": users.filter(is_banned=True).count(),

            "total_listings": listings.count(),
            "active_listings": listings.filter(
                status=Listing.STATUS_ACTIVE,
            ).count(),
            
            "pending_listings": listings.filter(
                status=Listing.STATUS_PENDING,
            ).count(),
            "rejected_listings": listings.filter(
                status=Listing.STATUS_REJECTED,
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

            "total_reports": reports.count(),
            "unresolved_reports": reports.filter(
                is_resolved=False,
            ).count(),
            "resolved_reports": reports.filter(
                is_resolved=True,
            ).count(),

            "total_payments": payments.count(),
            "pending_payments": payments.filter(
                status=Payment.STATUS_PENDING,
            ).count(),
            "paid_payments": payments.filter(
                status=Payment.STATUS_PAID,
            ).count(),
            "failed_payments": payments.filter(
                status=Payment.STATUS_FAILED,
            ).count(),

            "total_revenue": total_revenue,
            "featured_listing_revenue": featured_listing_revenue,
            "boost_listing_revenue": boost_listing_revenue,

            "today_revenue": today_revenue,
            "this_week_revenue": this_week_revenue,
            "this_month_revenue": this_month_revenue,

            "today_paid_payments": today_paid.count(),
            "this_week_paid_payments": this_week_paid.count(),
            "this_month_paid_payments": this_month_paid.count(),
        }

        serializer = AdminDashboardSerializer(data)

        return Response(serializer.data, status=status.HTTP_200_OK)
    


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

        create_payment_paid_notification(payment)

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
            payment = Payment.objects.select_related(
                "user",
                "listing",
            ).get(pk=pk)
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

        create_payment_failed_notification(payment)

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