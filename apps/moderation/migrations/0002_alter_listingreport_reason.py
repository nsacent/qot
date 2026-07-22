from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("moderation", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="listingreport",
            name="reason",
            field=models.CharField(
                choices=[
                    ("scam", "Scam or Fraud"),
                    ("fake", "Fake or Misleading Advert"),
                    ("wrong_price", "Wrong or Misleading Price"),
                    ("duplicate", "Duplicate Listing"),
                    ("wrong_category", "Wrong Category"),
                    ("prohibited", "Prohibited Item"),
                    ("sold_but_active", "Sold but Still Active"),
                    ("suspicious_seller", "Suspicious Seller"),
                    ("offensive", "Offensive or Inappropriate Content"),
                    ("other", "Other"),
                ],
                db_index=True,
                max_length=50,
            ),
        ),
    ]
