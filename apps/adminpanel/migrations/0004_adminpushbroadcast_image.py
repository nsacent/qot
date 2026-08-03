from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("adminpanel", "0003_adminpushbroadcast"),
    ]

    operations = [
        migrations.AddField(
            model_name="adminpushbroadcast",
            name="image",
            field=models.ImageField(
                blank=True,
                upload_to="admin/push-notifications/%Y/%m/",
            ),
        ),
    ]
