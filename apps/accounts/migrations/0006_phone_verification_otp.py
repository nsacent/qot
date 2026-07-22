from django.db import migrations, models


def invalidate_legacy_plaintext_codes(apps, schema_editor):
    VerificationCode = apps.get_model("accounts", "VerificationCode")
    VerificationCode.objects.filter(is_used=False).update(is_used=True)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_userprofile_cover_photo_userprofile_default_city_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="phone_verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RemoveIndex(
            model_name="verificationcode",
            name="accounts_ve_code_20ccee_idx",
        ),
        migrations.AlterField(
            model_name="verificationcode",
            name="code",
            field=models.CharField(editable=False, max_length=128),
        ),
        migrations.AddField(
            model_name="verificationcode",
            name="failed_attempts",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.RunPython(
            invalidate_legacy_plaintext_codes,
            migrations.RunPython.noop,
        ),
    ]
