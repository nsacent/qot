from django.urls import path

from .views import PublicSellerDetailAPIView, PublicSellerListingListAPIView


app_name = "sellers"


urlpatterns = [
    path("<int:seller_id>/", PublicSellerDetailAPIView.as_view(), name="seller_detail"),
    path("<int:seller_id>/listings/", PublicSellerListingListAPIView.as_view(), name="seller_listings"),
]