import django_filters
from django.db.models import Q

from .models import Listing


class ListingFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method="search")
    category = django_filters.CharFilter(field_name="category__slug")
    city = django_filters.CharFilter(field_name="city__slug")
    region = django_filters.CharFilter(field_name="city__region__slug")

    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")

    condition = django_filters.CharFilter(field_name="condition")
    status = django_filters.CharFilter(field_name="status")

    seller = django_filters.NumberFilter(field_name="seller_id")

    sort = django_filters.CharFilter(method="sort_results")

    class Meta:
        model = Listing
        fields = [
            "q",
            "category",
            "city",
            "region",
            "min_price",
            "max_price",
            "condition",
            "status",
            "seller",
            "sort",
        ]

    def search(self, queryset, name, value):
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

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)

        normal_params = {
            "page",
            "page_size",
            "q",
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
        }

        for key, value in self.request.query_params.items():
            if key in normal_params:
                continue

            if value in [None, ""]:
                continue

            queryset = self.filter_by_attribute(queryset, key, value)

        return queryset.distinct()

    def filter_by_attribute(self, queryset, key, value):
        value_lower = str(value).lower()

        if value_lower in ["true", "false"]:
            boolean_value = value_lower == "true"

            return queryset.filter(
                attributes__category_filter__key=key,
                attributes__value_boolean=boolean_value,
            )

        try:
            number_value = float(value)

            number_match = queryset.filter(
                attributes__category_filter__key=key,
                attributes__value_number=number_value,
            )

            if number_match.exists():
                return number_match

        except ValueError:
            pass

        return queryset.filter(
            attributes__category_filter__key=key,
            attributes__value_text__iexact=value,
        )

    def sort_results(self, queryset, name, value):
        sort_options = {
            "newest": "-created_at",
            "oldest": "created_at",
            "price_low": "price",
            "price_high": "-price",
            "popular": "-views_count",
            "featured": "-is_featured",
        }

        ordering = sort_options.get(value)

        if ordering:
            return queryset.order_by(ordering)

        return queryset.order_by("-created_at")