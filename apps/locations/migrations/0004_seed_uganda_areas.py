from django.db import migrations
from django.utils.text import slugify

from apps.locations.uganda_areas import UGANDA_AREAS


def seed_uganda_areas(apps, schema_editor):
    City = apps.get_model("locations", "City")
    Area = apps.get_model("locations", "Area")

    for city in City.objects.all().iterator():
        for name in UGANDA_AREAS.get(city.slug, []):
            Area.objects.update_or_create(
                city=city,
                slug=slugify(name),
                defaults={"name": name, "is_active": True},
            )


class Migration(migrations.Migration):
    dependencies = [
        ("locations", "0003_seed_kampala_divisions"),
    ]

    operations = [
        migrations.RunPython(seed_uganda_areas, migrations.RunPython.noop),
    ]
