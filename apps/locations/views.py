from rest_framework import generics, permissions

from .models import Region, City
from .serializers import RegionSerializer, CitySerializer


class RegionListAPIView(generics.ListAPIView):
    serializer_class = RegionSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        return (
            Region.objects
            .filter(is_active=True)
            .prefetch_related("cities")
            .order_by("name")
        )


class CityListAPIView(generics.ListAPIView):
    serializer_class = CitySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        queryset = (
            City.objects
            .filter(is_active=True, region__is_active=True)
            .select_related("region")
            .order_by("name")
        )

        region_slug = self.request.query_params.get("region")

        if region_slug:
            queryset = queryset.filter(region__slug=region_slug)

        return queryset
