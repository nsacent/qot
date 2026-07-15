from django.urls import path

from .views import (
    SellerDashboardAPIView,
    SellerListingListAPIView,
    SellerAnalyticsSummaryAPIView,
    SellerListingAnalyticsAPIView,
    SellerListingDetailAPIView,

)


app_name = "seller"


urlpatterns = [
    path("dashboard/", SellerDashboardAPIView.as_view(), name="dashboard"),
    path("listings/", SellerListingListAPIView.as_view(), name="listings"),
    path("analytics/", SellerAnalyticsSummaryAPIView.as_view(), name="seller_analytics"),
    path("listings/<int:pk>/", SellerListingDetailAPIView.as_view(), name="seller_listing_detail"),
    path("listings/<int:pk>/analytics/", SellerListingAnalyticsAPIView.as_view(), name="seller_listing_analytics"),
]