from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0002_promotionpackage_payment_package"),
    ]

    operations = [
        migrations.AlterField(
            model_name="payment",
            name="purpose",
            field=models.CharField(
                choices=[
                    ("featured_listing", "Featured Listing"),
                    ("boost_listing", "Boost Listing"),
                    ("homepage_promotion", "Homepage Promotion"),
                    ("subscription", "Subscription"),
                ],
                max_length=50,
            ),
        ),
    ]
