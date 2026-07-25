from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chats", "0005_chatmessage_reply_to_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatmessage",
            name="offer_amount",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=14,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="chatmessage",
            name="offer_status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("pending", "Pending"),
                    ("accepted", "Accepted"),
                    ("declined", "Declined"),
                    ("withdrawn", "Withdrawn"),
                ],
                max_length=20,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="chatmessage",
            name="message_type",
            field=models.CharField(
                choices=[
                    ("text", "Text"),
                    ("image", "Image"),
                    ("offer", "Offer"),
                ],
                default="text",
                max_length=20,
            ),
        ),
    ]
