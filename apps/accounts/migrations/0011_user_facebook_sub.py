from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0010_user_last_seen_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="facebook_sub",
            field=models.CharField(
                blank=True,
                editable=False,
                max_length=255,
                null=True,
                unique=True,
            ),
        ),
    ]
