from rest_framework import serializers

from apps.listings.serializers import ListingListSerializer

from .models import Favorite


class FavoriteSerializer(serializers.ModelSerializer):
    listing = ListingListSerializer(read_only=True)

    class Meta:
        model = Favorite
        fields = [
            "id",
            "listing",
            "created_at",
        ]