from .catalog import specs_for_slug


def sync_category_filter_catalog(
    Category,
    CategoryFilter,
    CategoryFilterOption,
    *,
    using="default",
):
    """Make stored category specs match the canonical catalog without data loss."""
    stats = {
        "categories": 0,
        "filters_created": 0,
        "filters_updated": 0,
        "filters_hidden": 0,
        "options_created": 0,
        "options_updated": 0,
        "options_hidden": 0,
    }

    categories = Category.objects.using(using).all()

    for category in categories.iterator():
        specs = specs_for_slug(category.slug)
        desired_keys = {spec["key"] for spec in specs}
        stats["categories"] += 1

        stale_filters = CategoryFilter.objects.using(using).filter(category=category).exclude(
            key__in=desired_keys
        )
        stats["filters_hidden"] += stale_filters.filter(is_searchable=True).count()
        stale_filters.update(is_searchable=False, is_required=False)

        for sort_order, spec in enumerate(specs):
            category_filter, created = CategoryFilter.objects.using(using).update_or_create(
                category=category,
                key=spec["key"],
                defaults={
                    "name": spec["name"],
                    "filter_type": spec["filter_type"],
                    "is_required": False,
                    "is_searchable": True,
                    "sort_order": sort_order,
                },
            )
            stats["filters_created" if created else "filters_updated"] += 1

            desired_values = set(spec["options"])
            stale_options = CategoryFilterOption.objects.using(using).filter(
                category_filter=category_filter
            ).exclude(value__in=desired_values)
            stats["options_hidden"] += stale_options.filter(is_active=True).count()
            stale_options.update(is_active=False)

            for option_order, option in enumerate(spec["options"]):
                _, option_created = CategoryFilterOption.objects.using(using).update_or_create(
                    category_filter=category_filter,
                    value=option,
                    defaults={
                        "label": option,
                        "sort_order": option_order,
                        "is_active": True,
                    },
                )
                stats["options_created" if option_created else "options_updated"] += 1

    return stats
