from django.urls import path

from .views import SellerDashboardAPIView, SellerListingListAPIView


app_name = "seller"


urlpatterns = [
    path("dashboard/", SellerDashboardAPIView.as_view(), name="dashboard"),
    path("listings/", SellerListingListAPIView.as_view(), name="listings"),
]