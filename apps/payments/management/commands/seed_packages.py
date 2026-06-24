from django.core.management.base import BaseCommand

from apps.payments.models import PromotionPackage


class Command(BaseCommand):
    help = "Seed default promotion packages."

    def handle(self, *args, **options):
        packages = [
            {
                "name": "Featured 7 Days",
                "package_type": PromotionPackage.TYPE_FEATURED_LISTING,
                "description": "Feature your listing for 7 days.",
                "duration_days": 7,
                "price": 10000,
                "currency": "UGX",
                "sort_order": 1,
            },
            {
                "name": "Featured 14 Days",
                "package_type": PromotionPackage.TYPE_FEATURED_LISTING,
                "description": "Feature your listing for 14 days.",
                "duration_days": 14,
                "price": 18000,
                "currency": "UGX",
                "sort_order": 2,
            },
            {
                "name": "Boost 3 Days",
                "package_type": PromotionPackage.TYPE_BOOST_LISTING,
                "description": "Boost your listing for 3 days.",
                "duration_days": 3,
                "price": 5000,
                "currency": "UGX",
                "sort_order": 3,
            },
        ]

        for item in packages:
            PromotionPackage.objects.update_or_create(
                name=item["name"],
                defaults=item,
            )

        self.stdout.write(
            self.style.SUCCESS("Promotion packages seeded successfully.")
        )