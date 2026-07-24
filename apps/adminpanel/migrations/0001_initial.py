from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AdminActivityLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("actor_name", models.CharField(blank=True, max_length=180)),
                ("actor_email", models.EmailField(blank=True, max_length=254)),
                ("actor_role", models.CharField(blank=True, db_index=True, max_length=20)),
                ("action", models.CharField(db_index=True, max_length=120)),
                ("description", models.CharField(max_length=255)),
                ("method", models.CharField(max_length=10)),
                ("path", models.CharField(max_length=500)),
                ("target_type", models.CharField(blank=True, db_index=True, max_length=80)),
                ("target_id", models.CharField(blank=True, max_length=180)),
                ("status_code", models.PositiveSmallIntegerField(db_index=True)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="admin_activity_logs", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="adminactivitylog",
            index=models.Index(fields=["actor", "-created_at"], name="adminlog_actor_created_idx"),
        ),
        migrations.AddIndex(
            model_name="adminactivitylog",
            index=models.Index(fields=["action", "-created_at"], name="adminlog_action_created_idx"),
        ),
    ]
