from django.core.management.base import BaseCommand

from apps.listings.image_processing import generate_listing_variants
from apps.listings.models import ListingImage, PendingListingImage


class Command(BaseCommand):
    help = "Add the QOT watermark to existing advert and staged images."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Count unwatermarked images without changing files.",
        )
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Regenerate every public image using the latest watermark style.",
        )

    def handle(self, *args, **options):
        image_filter = {} if options["refresh"] else {"is_watermarked": False}
        querysets = (
            ("advert", ListingImage.objects.filter(**image_filter)),
            ("staged", PendingListingImage.objects.filter(**image_filter)),
        )
        total = sum(queryset.count() for _, queryset in querysets)

        if options["dry_run"]:
            action = "to refresh" if options["refresh"] else "awaiting a watermark"
            self.stdout.write(f"Found {total} image(s) {action}.")
            return

        completed = 0
        failed = 0

        for label, queryset in querysets:
            for image_record in queryset.iterator():
                source = image_record.source_image or image_record.image

                if not source:
                    failed += 1
                    continue

                try:
                    variants = generate_listing_variants(source)
                    old_files = [
                        (field.storage, field.name)
                        for field in (
                            image_record.image,
                            image_record.card_image,
                            image_record.social_image,
                        )
                        if field and field.name
                    ]

                    image_record.image.save(
                        variants.detail.name,
                        variants.detail,
                        save=False,
                    )
                    image_record.card_image.save(
                        variants.card.name,
                        variants.card,
                        save=False,
                    )
                    image_record.social_image.save(
                        variants.social.name,
                        variants.social,
                        save=False,
                    )
                    image_record.is_watermarked = True
                    image_record.save(
                        update_fields=[
                            "image",
                            "card_image",
                            "social_image",
                            "is_watermarked",
                        ]
                    )

                    new_names = {
                        image_record.image.name,
                        image_record.card_image.name,
                        image_record.social_image.name,
                    }
                    source_name = (
                        image_record.source_image.name
                        if image_record.source_image
                        else ""
                    )
                    for storage, old_name in old_files:
                        if old_name not in new_names and old_name != source_name:
                            storage.delete(old_name)

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
