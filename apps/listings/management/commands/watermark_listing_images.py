from django.core.management.base import BaseCommand

from apps.listings.models import ListingImage, PendingListingImage
from apps.listings.watermarks import add_qot_watermark


class Command(BaseCommand):
    help = "Add the QOT watermark to existing advert and staged images."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Count unwatermarked images without changing files.",
        )

    def handle(self, *args, **options):
        querysets = (
            ("advert", ListingImage.objects.filter(is_watermarked=False)),
            ("staged", PendingListingImage.objects.filter(is_watermarked=False)),
        )
        total = sum(queryset.count() for _, queryset in querysets)

        if options["dry_run"]:
            self.stdout.write(f"Found {total} image(s) awaiting a QOT watermark.")
            return

        completed = 0
        failed = 0

        for label, queryset in querysets:
            for image_record in queryset.iterator():
                if not image_record.image:
                    failed += 1
                    continue

                original_name = image_record.image.name

                try:
                    watermarked_file = add_qot_watermark(image_record.image)
                    storage = image_record.image.storage
                    saved_name = storage.save(original_name, watermarked_file)
                    type(image_record).objects.filter(pk=image_record.pk).update(
                        image=saved_name,
                        is_watermarked=True,
                    )

                    if saved_name != original_name:
                        storage.delete(original_name)

                    completed += 1
                except (OSError, ValueError) as error:
                    failed += 1
                    self.stderr.write(
                        self.style.WARNING(
                            f"Skipped {label} image {image_record.pk}: {error}"
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Watermarked {completed} image(s); skipped {failed}."
            )
        )
