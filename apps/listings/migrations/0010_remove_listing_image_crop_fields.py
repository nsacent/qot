from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("listings", "0009_listing_image_variants"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="listingimage",
            name="crop_x",
        ),
        migrations.RemoveField(
            model_name="listingimage",
            name="crop_y",
        ),
        migrations.RemoveField(
            model_name="listingimage",
            name="crop_zoom",
        ),
        migrations.RemoveField(
            model_name="pendinglistingimage",
            name="crop_x",
        ),
        migrations.RemoveField(
            model_name="pendinglistingimage",
            name="crop_y",
        ),
        migrations.RemoveField(
            model_name="pendinglistingimage",
            name="crop_zoom",
        ),
    ]
