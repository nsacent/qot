from django.urls import path

from .views import (
    SellerReviewCreateAPIView,
    SellerReviewListAPIView,
    MyGivenReviewsAPIView,
    SellerReviewSummaryAPIView,
)


app_name = "reviews"


urlpatterns = [
    path("", SellerReviewCreateAPIView.as_view(), name="create_review"),
    path("me/", MyGivenReviewsAPIView.as_view(), name="my_reviews"),
    path("sellers/<int:seller_id>/", SellerReviewListAPIView.as_view(), name="seller_reviews"),
    path("sellers/<int:seller_id>/summary/", SellerReviewSummaryAPIView.as_view(), name="seller_review_summary"),
]