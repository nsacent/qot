from django.urls import path

from .views import (
    PublicSellerListAPIView,
    PublicSellerDetailAPIView,
    PublicSellerListingListAPIView,
    SellerFollowAPIView,
    SellerFollowersAPIView,
    SellerFollowingAPIView,
)


app_name = "sellers"


urlpatterns = [
    path("", PublicSellerListAPIView.as_view(), name="seller_list"),
    path("<int:seller_id>/", PublicSellerDetailAPIView.as_view(), name="seller_detail"),
    path("<int:seller_id>/listings/", PublicSellerListingListAPIView.as_view(), name="seller_listings"),
    path("<int:seller_id>/follow/", SellerFollowAPIView.as_view(), name="seller_follow"),
    path("<int:seller_id>/followers/", SellerFollowersAPIView.as_view(), name="seller_followers"),
    path("<int:seller_id>/following/", SellerFollowingAPIView.as_view(), name="seller_following"),
]
