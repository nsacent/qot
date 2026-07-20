from rest_framework import serializers

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

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "icon",
            "sort_order",
            "listings_count",
        ]


class CategorySerializer(serializers.ModelSerializer):
    children = CategoryChildSerializer(many=True, read_only=True)
    listings_count = serializers.IntegerField(read_only=True, default=0)

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
            "children",
        ]


class CategoryDetailSerializer(serializers.ModelSerializer):
    children = CategoryChildSerializer(many=True, read_only=True)
    filters = CategoryFilterSerializer(many=True, read_only=True)
    listings_count = serializers.IntegerField(read_only=True, default=0)

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
            "children",
            "filters",
        ]
