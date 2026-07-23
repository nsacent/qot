from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("listings", "0006_image_content_hashes"),
    ]

    operations = [
        migrations.AddField(
            model_name="listingimage",
            name="is_watermarked",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="pendinglistingimage",
            name="is_watermarked",
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]
