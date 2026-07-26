from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("listings", "0012_alter_listing_condition"),
    ]

    operations = [
        migrations.AddField(
            model_name="listing",
            name="review_original_snapshot",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="listing",
            name="review_submission_type",
            field=models.CharField(
                choices=[("new", "New ad"), ("edit", "Edited ad")],
                db_index=True,
                default="new",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="listing",
            name="submitted_for_review_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
