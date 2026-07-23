from datetime import timedelta
from decimal import Decimal, InvalidOperation

import django_filters
from django.db.models import Q
from django.utils import timezone

from .models import Listing


RESERVED_FILTER_PARAMS = {
    "page",
    "page_size",
    "q",
    "search",
    "category",
    "city",
    "region",
    "min_price",
    "max_price",
    "condition",
    "status",
    "seller",
    "sort",
    "mine",
    "is_negotiable",
    "negotiable",
    "verified_seller",
    "posted_within",
}


def split_values(value):
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


class ListingFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method="filter_search")
    search = django_filters.CharFilter(method="filter_search")
    category = django_filters.CharFilter(method="filter_category")
    city = django_filters.CharFilter(method="filter_city")
    region = django_filters.CharFilter(method="filter_region")
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")
    condition = django_filters.CharFilter(method="filter_condition")
    status = django_filters.CharFilter(field_name="status")
    seller = django_filters.NumberFilter(field_name="seller_id")
    is_negotiable = django_filters.BooleanFilter(field_name="is_negotiable")
    negotiable = django_filters.BooleanFilter(field_name="is_negotiable")
    verified_seller = django_filters.BooleanFilter(method="filter_verified_seller")
    posted_within = django_filters.NumberFilter(method="filter_posted_within")
    sort = django_filters.CharFilter(method="sort_results")

    class Meta:
        model = Listing
        fields = [
            "q", "search", "category", "city", "region", "min_price",
            "max_price", "condition", "status", "seller", "is_negotiable",
            "negotiable", "verified_seller", "posted_within", "sort",
        ]

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(title__icontains=value)
            | Q(description__icontains=value)
            | Q(category__name__icontains=value)
            | Q(category__parent__name__icontains=value)
            | Q(city__name__icontains=value)
            | Q(city__region__name__icontains=value)
            | Q(seller__full_name__icontains=value)
            | Q(seller__phone__icontains=value)
            | Q(attributes__value_text__icontains=value)
        ).distinct()

    def filter_category(self, queryset, name, value):
        if not value:
            return queryset
        values = split_values(value)
        query = Q()
        for item in values:
            query |= (
                Q(category__slug=item)
                | Q(category__parent__slug=item)
                | Q(category__name__iexact=item)
                | Q(category__parent__name__iexact=item)
            )
        return queryset.filter(query)

    def filter_city(self, queryset, name, value):
        values = split_values(value)
        if not values:
            return queryset
        query = Q()
        for item in values:
            query |= Q(city__slug=item) | Q(city__name__iexact=item)
            if item.isdigit():
                query |= Q(city_id=int(item))
        return queryset.filter(query)

    def filter_region(self, queryset, name, value):
        values = split_values(value)
        if not values:
            return queryset
        query = Q()
        for item in values:
            query |= Q(city__region__slug=item) | Q(city__region__name__iexact=item)
            if item.isdigit():
                query |= Q(city__region_id=int(item))
        return queryset.filter(query)

    def filter_condition(self, queryset, name, value):
        values = split_values(value)
        return queryset.filter(condition__in=values) if values else queryset

    def filter_verified_seller(self, queryset, name, value):
        return queryset.filter(seller__is_verified=True) if value else queryset

    def filter_posted_within(self, queryset, name, value):
        if value is None or value <= 0:
            return queryset
        return queryset.filter(created_at__gte=timezone.now() - timedelta(days=float(value)))

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)

        for key, value in self.data.items():
            if key in RESERVED_FILTER_PARAMS or value in (None, ""):
                continue
            queryset = self.filter_by_attribute(queryset, key, value)

        return queryset.distinct()

    def filter_by_attribute(self, queryset, key, value):
        lookup = "exact"
        filter_key = key
        if key.endswith("_min"):
            filter_key, lookup = key[:-4], "gte"
        elif key.endswith("_max"):
            filter_key, lookup = key[:-4], "lte"

        if lookup != "exact":
            try:
                number_value = Decimal(str(value).replace(",", ""))
            except (InvalidOperation, ValueError):
                return queryset.none()
            return queryset.filter(**{
                "attributes__category_filter__key": filter_key,
                f"attributes__value_number__{lookup}": number_value,
            })

        values = split_values(value)
        lowered = [item.lower() for item in values]
        if len(values) == 1 and lowered[0] in ("true", "false"):
            return queryset.filter(
                attributes__category_filter__key=filter_key,
                attributes__value_boolean=(lowered[0] == "true"),
            )

        text_query = Q()
        for item in values:
            text_query |= Q(attributes__value_text__iexact=item)

        number_query = Q()
        for item in values:
            try:
                number_query |= Q(attributes__value_number=Decimal(item.replace(",", "")))
            except (InvalidOperation, ValueError):
                continue

        return queryset.filter(
            Q(attributes__category_filter__key=filter_key) & (text_query | number_query)
        )

    def sort_results(self, queryset, name, value):
        if value == "featured":
            return queryset.filter(is_featured=True).filter(
                Q(featured_until__isnull=True) | Q(featured_until__gt=timezone.now())
            ).order_by("-created_at")
        if value == "newest":
            return queryset.order_by("-created_at")
        if value == "oldest":
            return queryset.order_by("created_at")
        if value == "price_low":
            return queryset.order_by("price", "-created_at")
        if value == "price_high":
            return queryset.order_by("-price", "-created_at")
        if value in ("popular", "most_viewed"):
            return queryset.order_by("-views_count", "-created_at")
        return queryset.order_by("-is_featured", "-created_at")
