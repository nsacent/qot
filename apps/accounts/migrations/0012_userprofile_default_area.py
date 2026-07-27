from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("locations", "0002_area"),
        ("accounts", "0011_user_facebook_sub"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="default_area",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="default_user_profiles",
                to="locations.area",
            ),
        ),
    ]
