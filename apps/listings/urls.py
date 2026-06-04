from django.urls import path

from .views import (
    ListingListCreateAPIView,
    ListingDetailAPIView,
    MarkListingSoldAPIView,
    ListingImageUploadAPIView,
    ListingImageDeleteAPIView,
)
from apps.moderation.views import ListingReportCreateAPIView


app_name = "listings"


urlpatterns = [
    path("", ListingListCreateAPIView.as_view(), name="listing_list_create"),
    path("<int:pk>/", ListingDetailAPIView.as_view(), name="listing_detail"),
    path("<int:pk>/mark-sold/", MarkListingSoldAPIView.as_view(), name="mark_sold"),

    path("<int:pk>/images/", ListingImageUploadAPIView.as_view(), name="listing_image_upload"),
    path(
        "<int:pk>/images/<int:image_id>/",
        ListingImageDeleteAPIView.as_view(),
        name="listing_image_delete",
    ),

    path("<int:listing_id>/report/", ListingReportCreateAPIView.as_view(), name="listing_report"),
]