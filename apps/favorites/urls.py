from django.urls import path

from .views import FavoriteListAPIView, FavoriteToggleAPIView


app_name = "favorites"


urlpatterns = [
    path("", FavoriteListAPIView.as_view(), name="favorite_list"),
    path("<int:listing_id>/", FavoriteToggleAPIView.as_view(), name="favorite_toggle"),
]