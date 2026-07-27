from rest_framework import serializers

from apps.categories.models import Category
from apps.listings.models import Listing


class HomeListingSerializer(serializers.ModelSerializer):
    seller_name = serializers.CharField(source="seller.full_name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_parent_name = serializers.SerializerMethodField()
    city_name = serializers.CharField(source="city.name", read_only=True)
    area_name = serializers.CharField(source="area.name", read_only=True, allow_null=True)
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            "id",
            "title",
            "slug",
            "seller",
            "seller_name",
            "category",
            "category_name",
            "category_parent_name",
            "city",
            "city_name",
            "area",
            "area_name",
            "price",
            "currency",
            "condition",
            "is_negotiable",
            "is_featured",
            "views_count",
            "favorites_count",
            "primary_image",
            "created_at",
        ]

    def get_category_parent_name(self, obj):
        parent = getattr(obj.category, "parent", None)
        return parent.name if parent else None

    def get_primary_image(self, obj):
        image = obj.images.filter(is_primary=True).first() or obj.images.first()

        if not image or not image.image:
            return None

        display_image = image.card_image or image.image
        request = self.context.get("request")

        if request:
            return request.build_absolute_uri(display_image.url)

        return display_image.url


class HomeCategorySerializer(serializers.ModelSerializer):
    listings_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "icon",
            "listings_count",
        ]
