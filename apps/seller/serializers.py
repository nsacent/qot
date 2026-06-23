from rest_framework import serializers

from apps.listings.models import Listing


class SellerListingSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            "id",
            "title",
            "slug",
            "category",
            "category_name",
            "city",
            "city_name",
            "price",
            "currency",
            "condition",
            "status",
            "is_negotiable",
            "is_featured",
            "views_count",
            "favorites_count",
            "expires_at",
            "sold_at",
            "rejection_reason",
            "created_at",
            "updated_at",
            "primary_image",
        ]

    def get_primary_image(self, obj):
        image = obj.images.filter(is_primary=True).first() or obj.images.first()

        if not image:
            return None

        request = self.context.get("request")

        if request:
            return request.build_absolute_uri(image.image.url)

        return image.image.url