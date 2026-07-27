from rest_framework import serializers

from .models import Area, City, Region


class AreaSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source="city.name", read_only=True)
    region = serializers.IntegerField(source="city.region_id", read_only=True)
    region_name = serializers.CharField(source="city.region.name", read_only=True)

    class Meta:
        model = Area
        fields = [
            "id",
            "name",
            "slug",
            "city",
            "city_name",
            "region",
            "region_name",
        ]


class CitySerializer(serializers.ModelSerializer):
    region_name = serializers.CharField(source="region.name", read_only=True)
    areas = AreaSerializer(many=True, read_only=True)

    class Meta:
        model = City
        fields = [
            "id",
            "name",
            "slug",
            "region",
            "region_name",
            "areas",
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
