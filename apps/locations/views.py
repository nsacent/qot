from rest_framework import generics, permissions

from django.db.models import Prefetch, Q

from .models import Area, City, Region
from .serializers import AreaSerializer, CitySerializer, RegionSerializer


class RegionListAPIView(generics.ListAPIView):
    serializer_class = RegionSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        return (
            Region.objects
            .filter(is_active=True)
            .prefetch_related(
                Prefetch(
                    "cities",
                    queryset=City.objects.filter(is_active=True).prefetch_related(
                        Prefetch(
                            "areas",
                            queryset=Area.objects.filter(is_active=True).order_by("name"),
                        )
                    ),
                )
            )
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
            .prefetch_related(
                Prefetch(
                    "areas",
                    queryset=Area.objects.filter(is_active=True).order_by("name"),
                )
            )
            .order_by("name")
        )

        region_slug = self.request.query_params.get("region")

        if region_slug:
            queryset = queryset.filter(region__slug=region_slug)

        return queryset


class AreaListAPIView(generics.ListAPIView):
    serializer_class = AreaSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        queryset = (
            Area.objects
            .filter(
                is_active=True,
                city__is_active=True,
                city__region__is_active=True,
            )
            .select_related("city", "city__region")
            .order_by("name")
        )

        city = str(self.request.query_params.get("city") or "").strip()
        if city:
            city_query = Q(city__slug=city) | Q(city__name__iexact=city)
            if city.isdigit():
                city_query |= Q(city_id=int(city))
            queryset = queryset.filter(city_query)

        region = str(self.request.query_params.get("region") or "").strip()
        if region:
            region_query = (
                Q(city__region__slug=region)
                | Q(city__region__name__iexact=region)
            )
            if region.isdigit():
                region_query |= Q(city__region_id=int(region))
            queryset = queryset.filter(region_query)

        return queryset
