from django.core.management.base import BaseCommand
from django.db.models import Count

from apps.favorites.models import Favorite
from apps.listings.models import Listing


class Command(BaseCommand):
    help = "Synchronize listing favorites_count with actual favorites."

    def handle(self, *args, **options):
        Listing.objects.update(favorites_count=0)

        counts = (
            Favorite.objects
            .values("listing_id")
            .annotate(total=Count("id"))
        )

        updated = 0

        for item in counts:
            Listing.objects.filter(id=item["listing_id"]).update(
                favorites_count=item["total"]
            )
            updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Synchronized favorite counts for {updated} listing(s)."
            )
        )