from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q


from apps.common.permissions import IsNotBanned, IsVerifiedUser
from apps.listings.models import Listing
from apps.notifications.services import create_listing_rejected_notification
from apps.adminpanel.permissions import IsAdminOrModerator

from .models import ListingReport
from .serializers import (
    ListingReportCreateSerializer,
    AdminListingReportSerializer,
    ResolveReportSerializer,
    RejectReportedListingSerializer,
)


class ListingReportCreateAPIView(APIView):
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

        if listing.seller == request.user:
            return Response(
                {"detail": "You cannot report your own listing."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing_report = ListingReport.objects.filter(
            listing=listing,
            reporter=request.user,
            is_resolved=False,
        ).first()

        if existing_report:
            return Response(
                {"detail": "You have already reported this listing."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ListingReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        report = serializer.save(
            listing=listing,
            reporter=request.user,
        )

        return Response(
            ListingReportCreateSerializer(report).data,
            status=status.HTTP_201_CREATED,
        )


class AdminReportListAPIView(generics.ListAPIView):
    serializer_class = AdminListingReportSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsAdminOrModerator,
    ]

    def get_queryset(self):
        queryset = (
            ListingReport.objects
            .select_related(
                "listing",
                "listing__seller",
                "reporter",
                "resolved_by",
            )
            .order_by("-created_at")
        )

        search = self.request.query_params.get("search")
        reason = self.request.query_params.get("reason")
        is_resolved = self.request.query_params.get("is_resolved")
        reporter = self.request.query_params.get("reporter")
        listing = self.request.query_params.get("listing")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")

        if search:
            queryset = queryset.filter(
                Q(listing__title__icontains=search)
                | Q(listing__description__icontains=search)
                | Q(reporter__full_name__icontains=search)
                | Q(reporter__phone__icontains=search)
                | Q(description__icontains=search)
            )

        if reason:
            queryset = queryset.filter(reason=reason)

        if is_resolved == "true":
            queryset = queryset.filter(is_resolved=True)

        if is_resolved == "false":
            queryset = queryset.filter(is_resolved=False)

        if reporter:
            queryset = queryset.filter(reporter_id=reporter)

        if listing:
            queryset = queryset.filter(listing_id=listing)

        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)

        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        return queryset.distinct()
    

class AdminReportDetailAPIView(generics.RetrieveAPIView):
    serializer_class = AdminListingReportSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsAdminOrModerator,
    ]

    queryset = ListingReport.objects.select_related(
        "listing",
        "reporter",
        "resolved_by",
    )


class ResolveReportAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsAdminOrModerator,
    ]

    def post(self, request, pk):
        try:
            report = ListingReport.objects.select_related("listing").get(pk=pk)
        except ListingReport.DoesNotExist:
            return Response(
                {"detail": "Report not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ResolveReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        report.is_resolved = True
        report.resolved_by = request.user
        report.resolved_at = timezone.now()
        report.save(update_fields=["is_resolved", "resolved_by", "resolved_at"])

        return Response(
            {
                "message": "Report resolved successfully.",
                "report": AdminListingReportSerializer(report).data,
            },
            status=status.HTTP_200_OK,
        )


class RejectReportedListingAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsAdminOrModerator,
    ]

    def post(self, request, pk):
        try:
            report = ListingReport.objects.select_related("listing").get(pk=pk)
        except ListingReport.DoesNotExist:
            return Response(
                {"detail": "Report not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = RejectReportedListingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        listing = report.listing
        listing.status = Listing.STATUS_REJECTED
        listing.rejection_reason = serializer.validated_data["rejection_reason"]
        listing.save(update_fields=["status", "rejection_reason", "updated_at"])

        report.is_resolved = True
        report.resolved_by = request.user
        report.resolved_at = timezone.now()
        report.save(update_fields=["is_resolved", "resolved_by", "resolved_at"])

        create_listing_rejected_notification(listing)

        return Response(
            {
                "message": "Listing rejected and report resolved successfully.",
                "report": AdminListingReportSerializer(report).data,
            },
            status=status.HTTP_200_OK,
        )


class DeleteReportedListingAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsAdminOrModerator,
    ]

    def post(self, request, pk):
        try:
            report = ListingReport.objects.select_related("listing").get(pk=pk)
        except ListingReport.DoesNotExist:
            return Response(
                {"detail": "Report not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        listing = report.listing
        listing.status = Listing.STATUS_DELETED
        listing.save(update_fields=["status", "updated_at"])

        report.is_resolved = True
        report.resolved_by = request.user
        report.resolved_at = timezone.now()
        report.save(update_fields=["is_resolved", "resolved_by", "resolved_at"])

        return Response(
            {
                "message": "Listing deleted and report resolved successfully.",
                "report": AdminListingReportSerializer(report).data,
            },
            status=status.HTTP_200_OK,
        )