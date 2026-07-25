from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("listings", "0011_alter_listing_description_alter_listing_title"),
    ]

    operations = [
        migrations.AlterField(
            model_name="listing",
            name="condition",
            field=models.CharField(
                choices=[
                    ("new", "New"),
                    ("used", "Used"),
                    ("refurbished", "Refurbished"),
                ],
                default="used",
                max_length=20,
            ),
        ),
    ]
