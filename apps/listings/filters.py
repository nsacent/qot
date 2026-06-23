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