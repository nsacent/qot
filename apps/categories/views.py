from rest_framework import generics, permissions

from .models import Category, CategoryFilter
from .serializers import (
    CategorySerializer,
    CategoryDetailSerializer,
    CategoryFilterSerializer,
)


class CategoryListAPIView(generics.ListAPIView):
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return (
            Category.objects
            .filter(is_active=True, parent__isnull=True)
            .prefetch_related("children")
            .order_by("sort_order", "name")
        )


class CategoryDetailAPIView(generics.RetrieveAPIView):
    serializer_class = CategoryDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"

    def get_queryset(self):
        return (
            Category.objects
            .filter(is_active=True)
            .prefetch_related(
                "children",
                "filters",
                "filters__options",
            )
        )


class CategoryFilterListAPIView(generics.ListAPIView):
    serializer_class = CategoryFilterSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        category_slug = self.kwargs.get("slug")

        return (
            CategoryFilter.objects
            .filter(
                category__slug=category_slug,
                category__is_active=True,
                is_searchable=True,
            )
            .prefetch_related("options")
            .order_by("sort_order", "name")
        )