from django.core.management.base import BaseCommand
from django.db import transaction

from apps.categories.catalog_sync import sync_category_filter_catalog
from apps.categories.models import Category, CategoryFilter, CategoryFilterOption


class Command(BaseCommand):
    help = "Synchronize category advert specifications with QOT's canonical catalog."

    def handle(self, *args, **options):
        with transaction.atomic():
            stats = sync_category_filter_catalog(
                Category,
                CategoryFilter,
                CategoryFilterOption,
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Category specifications synchronized: "
                f"{stats['categories']} categories, "
                f"{stats['filters_created']} filters created, "
                f"{stats['filters_hidden']} obsolete filters hidden, "
                f"{stats['options_created']} options created, "
                f"{stats['options_hidden']} obsolete options hidden."
            )
        )
