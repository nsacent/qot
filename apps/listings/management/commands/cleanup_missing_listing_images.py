from django.core.management.base import BaseCommand
from django.db import transaction

from apps.listings.models import Listing, ListingImage


class Command(BaseCommand):
    help = "Find listing image records whose uploaded file no longer exists."

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete-missing",
            action="store_true",
            help="Delete broken image records and repair primary-image selection.",
        )

    def handle(self, *args, **options):
        missing_images = [
            image
            for image in ListingImage.objects.select_related("listing")
            if image.image and not image.image.storage.exists(image.image.name)
        ]

        if not missing_images:
            self.stdout.write(self.style.SUCCESS("No missing listing image files found."))
            return

        self.stdout.write(
            self.style.WARNING(
                f"Found {len(missing_images)} listing image record(s) with missing files."
            )
        )

        if not options["delete_missing"]:
            self.stdout.write("Run again with --delete-missing to remove broken records.")
            return

        affected_listing_ids = {image.listing_id for image in missing_images}
        missing_image_ids = [image.id for image in missing_images]

        with transaction.atomic():
            ListingImage.objects.filter(id__in=missing_image_ids).delete()

            for listing in Listing.objects.filter(id__in=affected_listing_ids):
                images = listing.images.order_by("sort_order", "id")

                if images.exists() and not images.filter(is_primary=True).exists():
                    images.filter(pk=images.values_list("pk", flat=True).first()).update(
                        is_primary=True
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {len(missing_image_ids)} broken image record(s)."
            )
        )
