from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.listings.models import Listing
from apps.notifications.services import create_listing_expired_notification


class Command(BaseCommand):
    help = "Expire active listings whose expiry date has passed."

    def handle(self, *args, **options):
        now = timezone.now()

        listings = list(
            Listing.objects.filter(
                status=Listing.STATUS_ACTIVE,
                expires_at__isnull=False,
                expires_at__lt=now,
            ).select_related("seller")
        )

        count = 0

        for listing in listings:
            listing.status = Listing.STATUS_EXPIRED
            listing.save(update_fields=["status", "updated_at"])

            create_listing_expired_notification(listing)

            count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Expired {count} listing(s)."
            )
        )