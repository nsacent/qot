import hashlib

from django.db import migrations, models


def calculate_hash(image_file):
    digest = hashlib.sha256()

    try:
        image_file.open("rb")
        for chunk in image_file.chunks():
            digest.update(chunk)
        image_file.close()
    except (OSError, ValueError):
        return ""

    return digest.hexdigest()


def populate_existing_hashes(apps, schema_editor):
    for model_name in ("ListingImage", "PendingListingImage"):
        model = apps.get_model("listings", model_name)

        for image_record in model.objects.filter(content_hash="").iterator():
            if not image_record.image:
                continue

            content_hash = calculate_hash(image_record.image)
            if content_hash:
                model.objects.filter(pk=image_record.pk).update(
                    content_hash=content_hash
                )


class Migration(migrations.Migration):

    dependencies = [
        ("listings", "0005_pendinglistingimage_reserved_for_draft_listingdraft"),
    ]

    operations = [
        migrations.AddField(
            model_name="listingimage",
            name="content_hash",
            field=models.CharField(blank=True, db_index=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="pendinglistingimage",
            name="content_hash",
            field=models.CharField(blank=True, db_index=True, default="", max_length=64),
        ),
        migrations.RunPython(populate_existing_hashes, migrations.RunPython.noop),
    ]
