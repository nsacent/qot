from django.urls import path

from .views import (
    ListingListCreateAPIView,
    ListingDetailAPIView,
    MarkListingSoldAPIView,
)


app_name = "listings"


urlpatterns = [
    path("", ListingListCreateAPIView.as_view(), name="listing_list_create"),
    path("<int:pk>/", ListingDetailAPIView.as_view(), name="listing_detail"),
    path("<int:pk>/mark-sold/", MarkListingSoldAPIView.as_view(), name="mark_sold"),
]