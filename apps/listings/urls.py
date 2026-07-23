from django.urls import path

from .views import (
    ListingListCreateAPIView,
    ListingDetailAPIView,
    ListingImageUploadAPIView,
    ListingImageDeleteAPIView,
    CropListingImageAPIView,
    SetPrimaryListingImageAPIView,
    ReorderListingImagesAPIView,
    MarkListingSoldAPIView,
    MarkListingAvailableAPIView,
    MarkListingUnavailableAPIView,
    RelistListingAPIView,
    RenewListingAPIView,
    PendingListingImageAPIView,
    ListingDraftAPIView,
    ListingFacetsAPIView,
)
from apps.moderation.views import ListingReportCreateAPIView


app_name = "listings"


urlpatterns = [
    path("", ListingListCreateAPIView.as_view(), name="listing_list_create"),
    path("facets/", ListingFacetsAPIView.as_view(), name="listing_facets"),
    path("images/stage/", PendingListingImageAPIView.as_view(), name="stage_listing_image"),
    path("images/stage/<int:pk>/", PendingListingImageAPIView.as_view(), name="delete_staged_listing_image"),
    path("draft/", ListingDraftAPIView.as_view(), name="listing_draft"),
    path("<int:pk>/", ListingDetailAPIView.as_view(), name="listing_detail"),
    path("<int:pk>/mark-sold/", MarkListingSoldAPIView.as_view(), name="mark_sold"),
    path("<int:pk>/renew/", RenewListingAPIView.as_view(), name="renew_listing"),

    path("<int:pk>/images/", ListingImageUploadAPIView.as_view(), name="listing_image_upload"),
    path(
        "<int:pk>/images/<int:image_id>/",
        ListingImageDeleteAPIView.as_view(),
        name="listing_image_delete",
    ),
    path(
        "<int:pk>/images/<int:image_id>/set-primary/",
        SetPrimaryListingImageAPIView.as_view(),
        name="listing_image_set_primary",
    ),
    path(
        "<int:pk>/images/<int:image_id>/crop/",
        CropListingImageAPIView.as_view(),
        name="listing_image_crop",
    ),
    path(
        "<int:pk>/images/reorder/",
        ReorderListingImagesAPIView.as_view(),
        name="listing_images_reorder",
    ),

    path("<int:pk>/mark-available/", MarkListingAvailableAPIView.as_view(), name="mark_available"),
    path("<int:pk>/mark-unavailable/", MarkListingUnavailableAPIView.as_view(), name="mark_unavailable"),
    path("<int:pk>/relist/", RelistListingAPIView.as_view(), name="relist"),

    path("<int:listing_id>/report/", ListingReportCreateAPIView.as_view(), name="listing_report"),
]
