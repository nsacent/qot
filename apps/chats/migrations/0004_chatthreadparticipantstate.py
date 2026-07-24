from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("chats", "0003_chatreport_chatblock"),
    ]

    operations = [
        migrations.CreateModel(
            name="ChatThreadParticipantState",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("is_favourite", models.BooleanField(default=False)),
                ("is_archived", models.BooleanField(default=False)),
                ("is_spam", models.BooleanField(default=False)),
                ("is_marked_unread", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "thread",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="participant_states",
                        to="chats.chatthread",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="chat_thread_states",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="chatthreadparticipantstate",
            constraint=models.UniqueConstraint(
                fields=("thread", "user"),
                name="chats_unique_thread_user_state",
            ),
        ),
        migrations.AddIndex(
            model_name="chatthreadparticipantstate",
            index=models.Index(
                fields=["user", "is_archived", "is_spam"],
                name="chats_state_user_folder_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="chatthreadparticipantstate",
            index=models.Index(
                fields=["user", "is_favourite"],
                name="chats_state_user_fav_idx",
            ),
        ),
    ]
