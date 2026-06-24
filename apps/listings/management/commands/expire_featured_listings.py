from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.listings.models import Listing


class Command(BaseCommand):
    help = "Remove featured status from listings whose featured period has expired."

    def handle(self, *args, **options):
        now = timezone.now()

        queryset = Listing.objects.filter(
            is_featured=True,
            featured_until__isnull=False,
            featured_until__lt=now,
        )

        count = queryset.count()

        queryset.update(
            is_featured=False,
            featured_until=None,
            updated_at=now,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Unfeatured {count} expired featured listing(s)."
            )
        )