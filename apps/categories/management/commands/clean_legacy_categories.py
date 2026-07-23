from django.core.management.base import BaseCommand
from django.db import transaction

from apps.categories.models import Category
from apps.listings.models import Listing, ListingDraft


MERGES = {
    "phones-tablets": "mobile-phones",
    "phones": "mobile-phones",
    "laptops": "laptops-computers",
    "desktop-computers": "laptops-computers",
    "vehicle-spare-parts": "car-parts",
    "houses": "houses-for-sale",
    "land": "land-for-sale",
    "rentals": "houses-for-rent",
    "clothes": "fashion",
    "home-garden": "home-furniture",
}

REPARENTS = {
    "phone-accessories": "electronics",
    "furniture": "home-furniture",
}


class Command(BaseCommand):
    help = "Merge obsolete duplicate categories into the current marketplace catalog."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        moved_ads = 0
        moved_drafts = 0

        for source_slug, target_slug in MERGES.items():
            source = Category.objects.filter(slug=source_slug).first()
            target = Category.objects.filter(slug=target_slug, is_active=True).first()
            if not source or not target or source.pk == target.pk:
                continue

            moved_ads += Listing.objects.filter(category=source).count()
            if not dry_run:
                Listing.objects.filter(category=source).update(category=target)

            for draft in ListingDraft.objects.all().iterator():
                data = dict(draft.data or {})
                current = str(data.get("category") or data.get("category_id") or "")
                if current not in (str(source.pk), source.slug):
                    continue
                moved_drafts += 1
                if not dry_run:
                    if "category" in data:
                        data["category"] = target.pk
                    if "category_id" in data:
                        data["category_id"] = target.pk
                    draft.data = data
                    draft.save(update_fields=["data", "updated_at"])

            if not dry_run:
                source.is_active = False
                source.save(update_fields=["is_active", "updated_at"])

        for category_slug, parent_slug in REPARENTS.items():
            category = Category.objects.filter(slug=category_slug).first()
            parent = Category.objects.filter(slug=parent_slug, is_active=True).first()
            if category and parent and not dry_run:
                category.parent = parent
                category.is_active = True
                category.save(update_fields=["parent", "is_active", "updated_at"])

        if dry_run:
            transaction.set_rollback(True)
        action = "Would move" if dry_run else "Moved"
        self.stdout.write(self.style.SUCCESS(
            f"{action} {moved_ads} ad(s) and {moved_drafts} draft(s); legacy duplicates hidden."
        ))
