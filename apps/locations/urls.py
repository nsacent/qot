from django.urls import path

from .views import AreaListAPIView, CityListAPIView, RegionListAPIView


app_name = "locations"


urlpatterns = [
    path("regions/", RegionListAPIView.as_view(), name="region_list"),
    path("cities/", CityListAPIView.as_view(), name="city_list"),
    path("areas/", AreaListAPIView.as_view(), name="area_list"),
]
