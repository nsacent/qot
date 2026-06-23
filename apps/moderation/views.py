from django.utils import timezone

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.listings.models import Listing

from .models import ListingReport
from .permissions import IsAdminOrModerator
from .serializers import (
    ListingReportCreateSerializer,
    ListingReportSerializer,
    ListingReportResolveSerializer,
)

from apps.common.permissions import IsNotBanned, IsVerifiedUser

class ListingReportCreateAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBanned,
        IsVerifiedUser,
    ]

    def post(self, request, listing_id):
        try:
            listing = Listing.objects.exclude(
                status=Listing.STATUS_DELETED,
            ).get(pk=listing_id)
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

        serializer = ListingReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        report, created = ListingReport.objects.get_or_create(
            listing=listing,
            reporter=request.user,
            reason=serializer.validated_data["reason"],
            defaults={
                "description": serializer.validated_data.get("description", ""),
            },
        )

        if not created:
            return Response(
                {"detail": "You have already reported this listing for this reason."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": "Listing reported successfully.",
                "report": ListingReportSerializer(report).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ListingReportListAPIView(generics.ListAPIView):
    serializer_class = ListingReportSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrModerator]

    def get_queryset(self):
        queryset = (
            ListingReport.objects
            .select_related(
                "listing",
                "reporter",
                "resolved_by",
            )
            .order_by("-created_at")
        )

        is_resolved = self.request.query_params.get("is_resolved")
        reason = self.request.query_params.get("reason")

        if is_resolved == "true":
            queryset = queryset.filter(is_resolved=True)

        if is_resolved == "false":
            queryset = queryset.filter(is_resolved=False)

        if reason:
            queryset = queryset.filter(reason=reason)

        return queryset


class ListingReportResolveAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrModerator]

    def post(self, request, pk):
        try:
            report = ListingReport.objects.get(pk=pk)
        except ListingReport.DoesNotExist:
            return Response(
                {"detail": "Report not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if report.is_resolved:
            return Response(
                {"detail": "Report is already resolved."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ListingReportResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        report.is_resolved = True
        report.resolved_by = request.user
        report.resolved_at = timezone.now()
        report.resolution_note = serializer.validated_data.get("resolution_note", "")
        report.save(
            update_fields=[
                "is_resolved",
                "resolved_by",
                "resolved_at",
                "resolution_note",
            ]
        )

        return Response(
            {
                "message": "Report resolved successfully.",
                "report": ListingReportSerializer(report).data,
            },
            status=status.HTTP_200_OK,
        )