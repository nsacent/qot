from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.accounts.trust import calculate_user_trust_score


class Command(BaseCommand):
    help = "Recalculate trust scores for all users."

    def handle(self, *args, **options):
        users = User.objects.all()

        updated = 0

        for user in users:
            calculate_user_trust_score(user)
            updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Recalculated trust scores for {updated} user(s)."
            )
        )