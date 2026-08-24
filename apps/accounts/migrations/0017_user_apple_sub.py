from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0016_unique_alternative_phone"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="apple_sub",
            field=models.CharField(
                blank=True,
                editable=False,
                max_length=255,
                null=True,
                unique=True,
            ),
        ),
    ]
