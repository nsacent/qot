from django.urls import path

from .views import FavoriteListAPIView, FavoriteToggleAPIView


app_name = "favorites"


urlpatterns = [
    path("", FavoriteListAPIView.as_view(), name="favorite_list"),
    path(
        "listings/<int:listing_id>/toggle/",
        FavoriteToggleAPIView.as_view(),
        name="favorite_toggle",
    ),
]