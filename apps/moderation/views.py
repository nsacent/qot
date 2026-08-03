import logging

from django.db import transaction
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q


from apps.common.permissions import IsNotBanned, IsVerifiedUser
from apps.listings.models import Listing
from apps.notifications.services import (
    create_listing_deleted_notification,
    create_listing_rejected_notification,
    create_listing_report_resolved_notification,
    notify_admins_new_report,
)
from apps.adminpanel.permissions import IsAdminOrModerator
from apps.accounts.trust import calculate_user_trust_score

from .models import ListingReport
from .serializers import (
    ListingReportCreateSerializer,
    AdminListingReportSerializer,
    ListingDeleteSerializer,
    ResolveReportSerializer,
    RejectReportedListingSerializer,
)


logger = logging.getLogger(__name__)


def _finish_reported_listing_rejection(listing):
    try:
        create_listing_rejected_notification(listing)
    except Exception:
        logger.exception(
            "Unable to notify seller about rejected reported listing %s",
            listing.pk,
        )

    try:
        calculate_user_trust_score(listing.seller)
    except Exception:
        logger.exception(
            "Unable to recalculate trust score after rejecting reported listing %s",
            listing.pk,
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
        notify_admins_new_report(report)

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
        report.resolution_note = serializer.validated_data.get("note", "")
        report.save(update_fields=[
            "is_resolved",
            "resolved_by",
            "resolved_at",
            "resolution_note",
        ])
        create_listing_report_resolved_notification(report)

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

    @transaction.atomic
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
        listing.is_featured = False
        listing.featured_until = None
        listing.save(
            update_fields=[
                "status",
                "rejection_reason",
                "is_featured",
                "featured_until",
                "updated_at",
            ]
        )

        report.is_resolved = True
        report.resolved_by = request.user
        report.resolved_at = timezone.now()
        report.resolution_note = "The reported ad was rejected."
        report.save(update_fields=[
            "is_resolved",
            "resolved_by",
            "resolved_at",
            "resolution_note",
        ])

        _finish_reported_listing_rejection(listing)
        create_listing_report_resolved_notification(report)

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

        serializer = ListingDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        deletion_reason = serializer.validated_data["deletion_reason"]

        listing = report.listing
        with transaction.atomic():
            listing.status = Listing.STATUS_DELETED
            listing.is_featured = False
            listing.featured_until = None
            listing.save(
                update_fields=[
                    "status",
                    "is_featured",
                    "featured_until",
                    "updated_at",
                ]
            )

            report.is_resolved = True
            report.resolved_by = request.user
            report.resolved_at = timezone.now()
            report.resolution_note = "The reported ad was removed from QOT."
            report.save(update_fields=[
                "is_resolved",
                "resolved_by",
                "resolved_at",
                "resolution_note",
            ])

            create_listing_deleted_notification(listing, deletion_reason)
            create_listing_report_resolved_notification(report)

        return Response(
            {
                "message": "Listing deleted, seller notified, and report resolved.",
                "report": AdminListingReportSerializer(report).data,
            },
            status=status.HTTP_200_OK,
        )
