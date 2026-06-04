from rest_framework import serializers
from .models import Listing, ListingImage, ListingAttribute
from datetime import timedelta
from django.utils import timezone


class ListingImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingImage
        fields = [
            "id",
            "image",
            "is_primary",
            "sort_order",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
        ]


class ListingAttributeSerializer(serializers.ModelSerializer):
    filter_name = serializers.CharField(
        source="category_filter.name",
        read_only=True,
    )
    filter_key = serializers.CharField(
        source="category_filter.key",
        read_only=True,
    )
    filter_type = serializers.CharField(
        source="category_filter.filter_type",
        read_only=True,
    )

    class Meta:
        model = ListingAttribute
        fields = [
            "id",
            "category_filter",
            "filter_name",
            "filter_key",
            "filter_type",
            "value_text",
            "value_number",
            "value_boolean",
        ]


class ListingListSerializer(serializers.ModelSerializer):
    seller_name = serializers.CharField(source="seller.full_name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
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
            "primary_image",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "seller",
            "slug",
            "status",
            "views_count",
            "favorites_count",
            "created_at",
        ]

    def get_primary_image(self, obj):
        image = obj.images.filter(is_primary=True).first() or obj.images.first()

        if image and image.image:
            request = self.context.get("request")
            image_url = image.image.url

            if request:
                return request.build_absolute_uri(image_url)

            return image_url

        return None


class ListingDetailSerializer(serializers.ModelSerializer):
    seller_name = serializers.CharField(source="seller.full_name", read_only=True)
    seller_phone = serializers.CharField(source="seller.phone", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)

    images = ListingImageSerializer(many=True, read_only=True)
    attributes = ListingAttributeSerializer(many=True, read_only=True)

    class Meta:
        model = Listing
        fields = [
            "id",
            "title",
            "slug",
            "seller",
            "seller_name",
            "seller_phone",
            "category",
            "category_name",
            "city",
            "city_name",
            "description",
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
            "images",
            "attributes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "seller",
            "slug",
            "status",
            "views_count",
            "favorites_count",
            "sold_at",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]


class ListingCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Listing
        fields = [
            "id",
            "category",
            "city",
            "title",
            "description",
            "price",
            "currency",
            "condition",
            "is_negotiable",
        ]
        read_only_fields = [
            "id",
        ]

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than zero.")

        return value

    def create(self, validated_data):
        request = self.context["request"]

        return Listing.objects.create(
            seller=request.user,
            status=Listing.STATUS_PENDING,
            expires_at=timezone.now() + timedelta(days=30),
            **validated_data,
        )