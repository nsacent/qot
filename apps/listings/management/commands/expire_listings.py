from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.listings.models import Listing


class Command(BaseCommand):
    help = "Expire active listings whose expiry date has passed."

    def handle(self, *args, **options):
        now = timezone.now()

        queryset = Listing.objects.filter(
            status=Listing.STATUS_ACTIVE,
            expires_at__isnull=False,
            expires_at__lt=now,
        )

        count = queryset.count()

        queryset.update(
            status=Listing.STATUS_EXPIRED,
            updated_at=now,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Expired {count} listing(s)."
            )
        )