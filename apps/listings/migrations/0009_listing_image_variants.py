from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("listings", "0008_normalize_category_option_values"),
    ]

    operations = [
        migrations.AddField(
            model_name="listingimage",
            name="source_image",
            field=models.ImageField(blank=True, default="", upload_to="listings/source/"),
        ),
        migrations.AddField(
            model_name="listingimage",
            name="card_image",
            field=models.ImageField(blank=True, default="", upload_to="listings/cards/"),
        ),
        migrations.AddField(
            model_name="listingimage",
            name="social_image",
            field=models.ImageField(blank=True, default="", upload_to="listings/social/"),
        ),
        migrations.AddField(
            model_name="listingimage",
            name="crop_x",
            field=models.FloatField(default=0.5),
        ),
        migrations.AddField(
            model_name="listingimage",
            name="crop_y",
            field=models.FloatField(default=0.5),
        ),
        migrations.AddField(
            model_name="listingimage",
            name="crop_zoom",
            field=models.FloatField(default=1.0),
        ),
        migrations.AddField(
            model_name="pendinglistingimage",
            name="source_image",
            field=models.ImageField(blank=True, default="", upload_to="listings/source/"),
        ),
        migrations.AddField(
            model_name="pendinglistingimage",
            name="card_image",
            field=models.ImageField(blank=True, default="", upload_to="listings/cards/"),
        ),
        migrations.AddField(
            model_name="pendinglistingimage",
            name="social_image",
            field=models.ImageField(blank=True, default="", upload_to="listings/social/"),
        ),
        migrations.AddField(
            model_name="pendinglistingimage",
            name="crop_x",
            field=models.FloatField(default=0.5),
        ),
        migrations.AddField(
            model_name="pendinglistingimage",
            name="crop_y",
            field=models.FloatField(default=0.5),
        ),
        migrations.AddField(
            model_name="pendinglistingimage",
            name="crop_zoom",
            field=models.FloatField(default=1.0),
        ),
    ]
