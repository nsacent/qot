import django_filters

from .models import Listing


class ListingFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method="filter_search")

    category = django_filters.CharFilter(
        field_name="category__slug",
        lookup_expr="iexact",
    )

    city = django_filters.CharFilter(
        field_name="city__slug",
        lookup_expr="iexact",
    )

    region = django_filters.CharFilter(
        field_name="city__region__slug",
        lookup_expr="iexact",
    )

    min_price = django_filters.NumberFilter(
        field_name="price",
        lookup_expr="gte",
    )

    max_price = django_filters.NumberFilter(
        field_name="price",
        lookup_expr="lte",
    )

    condition = django_filters.CharFilter(
        field_name="condition",
        lookup_expr="iexact",
    )

    seller = django_filters.NumberFilter(
        field_name="seller_id",
    )

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset

        return queryset.filter(
            title__icontains=value
        ) | queryset.filter(
            description__icontains=value
        )

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
            "seller",
        ]