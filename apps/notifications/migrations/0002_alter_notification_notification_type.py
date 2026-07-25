from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notification",
            name="notification_type",
            field=models.CharField(
                choices=[
                    ("message", "New Message"),
                    ("listing_approved", "Ad Approved"),
                    ("listing_rejected", "Ad Rejected"),
                    ("listing_expired", "Ad Expired"),
                    ("favorite", "Ad Saved"),
                    ("follow", "New Follower"),
                    ("system", "System"),
                ],
                db_index=True,
                max_length=50,
            ),
        ),
    ]
