from rest_framework import serializers

from apps.listings.photo_requirements import get_category_photo_requirements

from .models import Category, CategoryFilter, CategoryFilterOption


class CategoryFilterOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryFilterOption
        fields = [
            "id",
            "label",
            "value",
            "sort_order",
        ]


class CategoryFilterSerializer(serializers.ModelSerializer):
    options = CategoryFilterOptionSerializer(many=True, read_only=True)

    class Meta:
        model = CategoryFilter
        fields = [
            "id",
            "name",
            "key",
            "filter_type",
            "is_required",
            "is_searchable",
            "sort_order",
            "options",
        ]


class CategoryChildSerializer(serializers.ModelSerializer):
    listings_count = serializers.IntegerField(read_only=True, default=0)
    minimum_photos = serializers.SerializerMethodField()
    maximum_photos = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "icon",
            "sort_order",
            "listings_count",
            "minimum_photos",
            "maximum_photos",
        ]

    def get_minimum_photos(self, obj):
        return get_category_photo_requirements(obj).minimum

    def get_maximum_photos(self, obj):
        return get_category_photo_requirements(obj).maximum


class CategorySerializer(serializers.ModelSerializer):
    children = CategoryChildSerializer(many=True, read_only=True)
    listings_count = serializers.IntegerField(read_only=True, default=0)
    minimum_photos = serializers.SerializerMethodField()
    maximum_photos = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "parent",
            "icon",
            "sort_order",
            "listings_count",
            "minimum_photos",
            "maximum_photos",
            "children",
        ]

    def get_minimum_photos(self, obj):
        return get_category_photo_requirements(obj).minimum

    def get_maximum_photos(self, obj):
        return get_category_photo_requirements(obj).maximum


class CategoryDetailSerializer(serializers.ModelSerializer):
    children = CategoryChildSerializer(many=True, read_only=True)
    filters = CategoryFilterSerializer(many=True, read_only=True)
    listings_count = serializers.IntegerField(read_only=True, default=0)
    minimum_photos = serializers.SerializerMethodField()
    maximum_photos = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "parent",
            "icon",
            "sort_order",
            "listings_count",
            "minimum_photos",
            "maximum_photos",
            "children",
            "filters",
        ]

    def get_minimum_photos(self, obj):
        return get_category_photo_requirements(obj).minimum

    def get_maximum_photos(self, obj):
        return get_category_photo_requirements(obj).maximum
