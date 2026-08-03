from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0005_notification_action_url_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="image_url",
            field=models.URLField(blank=True, max_length=1000),
        ),
    ]
