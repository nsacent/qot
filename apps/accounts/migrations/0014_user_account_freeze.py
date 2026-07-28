from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0013_smsdeliveryreport"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="frozen_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="is_frozen",
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]
