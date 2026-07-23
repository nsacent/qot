from django.db import migrations


def sync_category_filters(apps, schema_editor):
    from apps.categories.catalog_sync import sync_category_filter_catalog

    sync_category_filter_catalog(
        apps.get_model("categories", "Category"),
        apps.get_model("categories", "CategoryFilter"),
        apps.get_model("categories", "CategoryFilterOption"),
        using=schema_editor.connection.alias,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("categories", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(sync_category_filters, migrations.RunPython.noop),
    ]
