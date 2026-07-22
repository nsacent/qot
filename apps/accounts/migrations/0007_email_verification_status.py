from django.db import migrations, models
from django.utils import timezone


def preserve_existing_email_verification(apps, schema_editor):
    User = apps.get_model("accounts", "User")

    for user in User.objects.filter(
        is_verified=True,
        email__isnull=False,
        phone_verified_at__isnull=True,
    ).iterator():
        user.email_verified_at = user.updated_at or user.date_joined or timezone.now()
        user.save(update_fields=["email_verified_at"])


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0006_phone_verification_otp"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="email_verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(
            preserve_existing_email_verification,
            migrations.RunPython.noop,
        ),
    ]
