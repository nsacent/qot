from django.db import migrations, models

import apps.accounts.models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_user_google_sub"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="notification_preferences",
            field=models.JSONField(
                blank=True,
                default=apps.accounts.models.default_notification_preferences,
            ),
        ),
    ]
