from django.db.models import Count, F, Prefetch, Q
from django.utils import timezone
from rest_framework import generics, permissions

from .models import Category, CategoryFilter
from apps.listings.models import Listing
from .serializers import (
    CategorySerializer,
    CategoryDetailSerializer,
    CategoryFilterSerializer,
)


def active_listing_filter(prefix):
    return Q(**{f"{prefix}__status": Listing.STATUS_ACTIVE}) & (
        Q(**{f"{prefix}__expires_at__isnull": True})
        | Q(**{f"{prefix}__expires_at__gt": timezone.now()})
    )


def with_listing_counts(queryset):
    child_queryset = (
        Category.objects
        .filter(is_active=True)
        .annotate(
            listings_count=Count(
                "listings",
                filter=active_listing_filter("listings"),
                distinct=True,
            )
        )
        .order_by("sort_order", "name")
    )

    return (
        queryset
        .annotate(
            direct_listings_count=Count(
                "listings",
                filter=active_listing_filter("listings"),
                distinct=True,
            ),
            child_listings_count=Count(
                "children__listings",
                filter=active_listing_filter("children__listings"),
                distinct=True,
            ),
        )
        .annotate(
            listings_count=F("direct_listings_count") + F("child_listings_count")
        )
        .prefetch_related(Prefetch("children", queryset=child_queryset))
    )


class CategoryListAPIView(generics.ListAPIView):
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        return with_listing_counts(
            Category.objects
            .filter(is_active=True, parent__isnull=True)
            .order_by("sort_order", "name")
        )


class CategoryDetailAPIView(generics.RetrieveAPIView):
    serializer_class = CategoryDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"

    def get_queryset(self):
        return with_listing_counts(
            Category.objects
            .filter(is_active=True)
            .prefetch_related(
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
