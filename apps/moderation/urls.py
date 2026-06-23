from django.urls import path

from .views import (
    AdminReportListAPIView,
    AdminReportDetailAPIView,
    ResolveReportAPIView,
    RejectReportedListingAPIView,
    DeleteReportedListingAPIView,
)


app_name = "moderation"


urlpatterns = [
    path("reports/", AdminReportListAPIView.as_view(), name="report_list"),
    path("reports/<int:pk>/", AdminReportDetailAPIView.as_view(), name="report_detail"),
    path("reports/<int:pk>/resolve/", ResolveReportAPIView.as_view(), name="resolve_report"),
    path("reports/<int:pk>/reject-listing/", RejectReportedListingAPIView.as_view(), name="reject_reported_listing"),
    path("reports/<int:pk>/delete-listing/", DeleteReportedListingAPIView.as_view(), name="delete_reported_listing"),
]