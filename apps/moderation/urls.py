from django.urls import path

from .views import ListingReportListAPIView, ListingReportResolveAPIView


app_name = "moderation"


urlpatterns = [
    path("reports/", ListingReportListAPIView.as_view(), name="report_list"),
    path("reports/<int:pk>/resolve/", ListingReportResolveAPIView.as_view(), name="report_resolve"),
]