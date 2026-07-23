from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.listings.models import PendingListingImage
from apps.listings.image_processing import delete_listing_image_files


class Command(BaseCommand):
    help = "Delete staged listing photos that were abandoned more than 24 hours ago."

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(hours=24)
        pending_images = list(
            PendingListingImage.objects.filter(
                created_at__lt=cutoff,
                reserved_for_draft=False,
            )
        )

        for pending_image in pending_images:
            delete_listing_image_files(pending_image)
            pending_image.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {len(pending_images)} abandoned staged image(s)."
            )
        )
