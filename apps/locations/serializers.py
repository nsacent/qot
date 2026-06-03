from rest_framework import serializers

from .models import Region, City


class CitySerializer(serializers.ModelSerializer):
    region_name = serializers.CharField(source="region.name", read_only=True)

    class Meta:
        model = City
        fields = [
            "id",
            "name",
            "slug",
            "region",
            "region_name",
        ]


class RegionSerializer(serializers.ModelSerializer):
    cities = CitySerializer(many=True, read_only=True)

    class Meta:
        model = Region
        fields = [
            "id",
            "name",
            "slug",
            "cities",
        ]