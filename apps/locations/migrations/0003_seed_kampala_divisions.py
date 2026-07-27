from django.db import migrations
from django.utils.text import slugify


KAMPALA_DIVISIONS = [
    "Central",
    "Kawempe",
    "Makindye",
    "Nakawa",
    "Rubaga",
]


def seed_kampala_divisions(apps, schema_editor):
    City = apps.get_model("locations", "City")
    Area = apps.get_model("locations", "Area")

    kampala = City.objects.filter(slug="kampala").first()
    if not kampala:
        return

    for name in KAMPALA_DIVISIONS:
        Area.objects.update_or_create(
            city=kampala,
            slug=slugify(name),
            defaults={"name": name, "is_active": True},
        )


def remove_kampala_divisions(apps, schema_editor):
    City = apps.get_model("locations", "City")
    Area = apps.get_model("locations", "Area")

    kampala = City.objects.filter(slug="kampala").first()
    if kampala:
        Area.objects.filter(
            city=kampala,
            slug__in=[slugify(name) for name in KAMPALA_DIVISIONS],
        ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("locations", "0002_area"),
    ]

    operations = [
        migrations.RunPython(seed_kampala_divisions, remove_kampala_divisions),
    ]
