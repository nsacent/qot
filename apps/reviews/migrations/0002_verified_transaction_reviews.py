from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("chats", "0007_chatmessage_callback_fields"),
        ("reviews", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="sellerreview",
            name="communication_rating",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="sellerreview",
            name="is_verified_transaction",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="sellerreview",
            name="item_accuracy_rating",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="sellerreview",
            name="item_condition_rating",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="sellerreview",
            name="verified_offer",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="transaction_review",
                to="chats.chatmessage",
            ),
        ),
    ]
