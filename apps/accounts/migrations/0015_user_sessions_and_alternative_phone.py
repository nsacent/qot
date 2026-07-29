import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0014_user_account_freeze"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="facebook_sub",
        ),
        migrations.AddField(
            model_name="userprofile",
            name="alternative_phone",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.CreateModel(
            name="UserSession",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("refresh_jti", models.CharField(max_length=255, unique=True)),
                ("device_id", models.CharField(blank=True, db_index=True, max_length=255)),
                ("device_name", models.CharField(blank=True, max_length=255)),
                ("device_model", models.CharField(blank=True, max_length=255)),
                ("platform", models.CharField(choices=[("android", "Android"), ("ios", "iOS"), ("web", "Web"), ("unknown", "Unknown")], default="unknown", max_length=20)),
                ("os_name", models.CharField(blank=True, max_length=100)),
                ("os_version", models.CharField(blank=True, max_length=100)),
                ("app_version", models.CharField(blank=True, max_length=50)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.TextField(blank=True)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("last_seen_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="login_sessions", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-last_seen_at", "-created_at"],
                "indexes": [
                    models.Index(fields=["user", "is_active"], name="accounts_us_user_id_91ed82_idx"),
                    models.Index(fields=["user", "device_id"], name="accounts_us_user_id_377f93_idx"),
                ],
            },
        ),
    ]
