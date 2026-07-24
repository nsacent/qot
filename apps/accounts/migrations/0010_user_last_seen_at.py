from django.db import migrations, models
from django.db.models import F


def populate_last_seen(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(last_seen_at__isnull=True).update(
        last_seen_at=F("updated_at")
    )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0009_userprofile_timezone"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="last_seen_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.RunPython(populate_last_seen, migrations.RunPython.noop),
    ]
