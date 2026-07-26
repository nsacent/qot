from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chats", "0006_chatmessage_offer_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatmessage",
            name="callback_name",
            field=models.CharField(blank=True, default="", max_length=150),
        ),
        migrations.AddField(
            model_name="chatmessage",
            name="callback_phone",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AlterField(
            model_name="chatmessage",
            name="message_type",
            field=models.CharField(
                choices=[
                    ("text", "Text"),
                    ("image", "Image"),
                    ("offer", "Offer"),
                    ("callback", "Callback request"),
                ],
                default="text",
                max_length=20,
            ),
        ),
    ]
