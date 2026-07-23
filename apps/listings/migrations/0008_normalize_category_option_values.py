from collections import defaultdict

from django.db import migrations


def normalize_category_option_values(apps, schema_editor):
    ListingAttribute = apps.get_model("listings", "ListingAttribute")
    CategoryFilterOption = apps.get_model("categories", "CategoryFilterOption")

    option_values = defaultdict(set)
    option_values_by_id = defaultdict(dict)

    for option in CategoryFilterOption.objects.all().iterator():
        option_values[option.category_filter_id].add(str(option.value))
        option_values_by_id[option.category_filter_id][str(option.id)] = option.value

    changed_attributes = []
    attributes = ListingAttribute.objects.exclude(value_text__isnull=True).exclude(
        value_text=""
    )

    for attribute in attributes.iterator():
        raw_value = str(attribute.value_text).strip()
        filter_id = attribute.category_filter_id

        if raw_value in option_values[filter_id]:
            continue

        canonical_value = option_values_by_id[filter_id].get(raw_value)

        if canonical_value is None:
            continue

        attribute.value_text = canonical_value
        changed_attributes.append(attribute)

    if changed_attributes:
        ListingAttribute.objects.bulk_update(
            changed_attributes,
            ["value_text"],
            batch_size=500,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("categories", "0002_sync_category_filters"),
        ("listings", "0007_listing_image_watermarks"),
    ]

    operations = [
        migrations.RunPython(
            normalize_category_option_values,
            migrations.RunPython.noop,
        ),
    ]
