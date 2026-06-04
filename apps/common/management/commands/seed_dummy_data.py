from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.accounts.models import User
from apps.categories.models import Category, CategoryFilter, CategoryFilterOption
from apps.locations.models import Region, City
from apps.listings.models import Listing
from apps.favorites.models import Favorite
from apps.notifications.models import Notification
from apps.moderation.models import ListingReport


class Command(BaseCommand):
    help = "Seed dummy data for QOT classifieds platform"

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Seeding QOT dummy data..."))

        # Regions and cities
        central, _ = Region.objects.get_or_create(
            name="Central Region",
            slug="central-region",
        )

        western, _ = Region.objects.get_or_create(
            name="Western Region",
            slug="western-region",
        )

        eastern, _ = Region.objects.get_or_create(
            name="Eastern Region",
            slug="eastern-region",
        )

        northern, _ = Region.objects.get_or_create(
            name="Northern Region",
            slug="northern-region",
        )

        cities_data = [
            (central, "Kampala"),
            (central, "Wakiso"),
            (central, "Mukono"),
            (central, "Entebbe"),
            (western, "Mbarara"),
            (western, "Fort Portal"),
            (eastern, "Jinja"),
            (eastern, "Mbale"),
            (northern, "Gulu"),
            (northern, "Lira"),
        ]

        cities = {}

        for region, name in cities_data:
            city, _ = City.objects.get_or_create(
                region=region,
                name=name,
                slug=slugify(name),
            )
            cities[name] = city

                # Categories
        def get_category(name, slug, parent=None, sort_order=0):
            category, _ = Category.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "parent": parent,
                    "sort_order": sort_order,
                },
            )

            changed = False

            if category.name != name:
                category.name = name
                changed = True

            if category.parent != parent:
                category.parent = parent
                changed = True

            if category.sort_order != sort_order:
                category.sort_order = sort_order
                changed = True

            if changed:
                category.save(update_fields=["name", "parent", "sort_order", "updated_at"])

            return category

        vehicles = get_category("Vehicles", "vehicles", sort_order=1)
        cars = get_category("Cars", "cars", parent=vehicles, sort_order=1)

        phones_tablets = get_category("Phones & Tablets", "phones-tablets", sort_order=2)
        phones = get_category("Phones", "phones", parent=phones_tablets, sort_order=1)

        electronics = get_category("Electronics", "electronics", sort_order=3)
        laptops = get_category("Laptops", "laptops", parent=electronics, sort_order=1)

        property_cat = get_category("Property", "property", sort_order=4)
        houses_rent = get_category("Houses for Rent", "houses-for-rent", parent=property_cat, sort_order=1)

        furniture = get_category("Furniture", "furniture", sort_order=5)
        

        # Category filters
        def add_filter(category, name, key, filter_type, options=None):
            category_filter, _ = CategoryFilter.objects.get_or_create(
                category=category,
                key=key,
                defaults={
                    "name": name,
                    "filter_type": filter_type,
                    "is_required": False,
                    "is_searchable": True,
                },
            )

            if options:
                for index, option in enumerate(options):
                    CategoryFilterOption.objects.get_or_create(
                        category_filter=category_filter,
                        value=slugify(option),
                        defaults={
                            "label": option,
                            "sort_order": index,
                        },
                    )

            return category_filter

        add_filter(cars, "Brand", "brand", "select", ["Toyota", "Subaru", "Mercedes Benz", "BMW", "Nissan"])
        add_filter(cars, "Transmission", "transmission", "select", ["Automatic", "Manual"])
        add_filter(cars, "Fuel Type", "fuel-type", "select", ["Petrol", "Diesel", "Hybrid"])
        add_filter(cars, "Year", "year", "number")

        add_filter(phones, "Brand", "brand", "select", ["Apple", "Samsung", "Tecno", "Infinix", "Huawei"])
        add_filter(phones, "Storage", "storage", "select", ["64GB", "128GB", "256GB", "512GB"])
        add_filter(phones, "RAM", "ram", "select", ["4GB", "6GB", "8GB", "12GB"])

        add_filter(laptops, "Brand", "brand", "select", ["Dell", "HP", "Lenovo", "Apple", "Asus"])
        add_filter(laptops, "Processor", "processor", "select", ["Core i5", "Core i7", "Ryzen 5", "Ryzen 7", "M1"])
        add_filter(laptops, "RAM", "ram", "select", ["8GB", "16GB", "32GB"])

        add_filter(houses_rent, "Bedrooms", "bedrooms", "number")
        add_filter(houses_rent, "Furnished", "furnished", "boolean")
        add_filter(houses_rent, "Property Type", "property-type", "select", ["Apartment", "Standalone", "Studio", "Double Room"])

        # Users
        admin, _ = User.objects.get_or_create(
            phone="+256700000000",
            defaults={
                "email": "admin@qot.ug",
                "full_name": "QOT Admin",
                "role": "admin",
                "is_staff": True,
                "is_superuser": True,
                "is_verified": True,
            },
        )
        admin.set_password("AdminPass123")
        admin.save()

        seller1, _ = User.objects.get_or_create(
            phone="+256700000001",
            defaults={
                "email": "seller1@example.com",
                "full_name": "Brian Seller",
                "is_verified": True,
            },
        )
        seller1.set_password("StrongPass123")
        seller1.save()

        seller2, _ = User.objects.get_or_create(
            phone="+256700000002",
            defaults={
                "email": "seller2@example.com",
                "full_name": "Amina Seller",
                "is_verified": True,
            },
        )
        seller2.set_password("StrongPass123")
        seller2.save()

        buyer1, _ = User.objects.get_or_create(
            phone="+256700000003",
            defaults={
                "email": "buyer1@example.com",
                "full_name": "Daniel Buyer",
                "is_verified": True,
            },
        )
        buyer1.set_password("StrongPass123")
        buyer1.save()

        buyer2, _ = User.objects.get_or_create(
            phone="+256700000004",
            defaults={
                "email": "buyer2@example.com",
                "full_name": "Sarah Buyer",
                "is_verified": True,
            },
        )
        buyer2.set_password("StrongPass123")
        buyer2.save()

        # Listings
        listings_data = [
            {
                "seller": seller1,
                "category": phones,
                "city": cities["Kampala"],
                "title": "iPhone 13 Pro Max 256GB",
                "description": "Clean iPhone 13 Pro Max, original screen, good battery health, available in Kampala.",
                "price": Decimal("1800000"),
                "condition": "used",
                "status": "active",
            },
            {
                "seller": seller1,
                "category": laptops,
                "city": cities["Kampala"],
                "title": "Dell Latitude 5410 Core i7",
                "description": "Dell Latitude 5410, Core i7, 16GB RAM, 512GB SSD, good for office and school work.",
                "price": Decimal("1350000"),
                "condition": "used",
                "status": "active",
            },
            {
                "seller": seller2,
                "category": cars,
                "city": cities["Wakiso"],
                "title": "Toyota Premio 2010",
                "description": "Toyota Premio in good condition, automatic transmission, petrol engine, ready to drive.",
                "price": Decimal("28500000"),
                "condition": "used",
                "status": "active",
            },
            {
                "seller": seller2,
                "category": houses_rent,
                "city": cities["Mukono"],
                "title": "Two Bedroom Apartment for Rent",
                "description": "Spacious two bedroom apartment in Mukono, secure compound, near the main road.",
                "price": Decimal("650000"),
                "condition": "used",
                "status": "active",
            },
            {
                "seller": seller1,
                "category": phones,
                "city": cities["Mbarara"],
                "title": "Samsung Galaxy S22 Ultra",
                "description": "Samsung Galaxy S22 Ultra, 256GB storage, clean body, great camera.",
                "price": Decimal("1600000"),
                "condition": "used",
                "status": "pending",
            },
            {
                "seller": seller2,
                "category": laptops,
                "city": cities["Jinja"],
                "title": "Lenovo ThinkPad X390 Touchscreen",
                "description": "Lenovo ThinkPad X390, Core i5 8th Gen, 8GB RAM, 256GB SSD, touchscreen.",
                "price": Decimal("850000"),
                "condition": "used",
                "status": "active",
            },
        ]

        created_listings = []

        for item in listings_data:
            listing, created = Listing.objects.get_or_create(
                title=item["title"],
                seller=item["seller"],
                defaults={
                    "category": item["category"],
                    "city": item["city"],
                    "description": item["description"],
                    "price": item["price"],
                    "currency": "UGX",
                    "condition": item["condition"],
                    "status": item["status"],
                    "is_negotiable": True,
                    "slug": "temp",
                },
            )

            if created or listing.slug == "temp":
                listing.slug = f"{slugify(listing.title)}-{listing.id}"
                listing.save(update_fields=["slug"])

            created_listings.append(listing)

        # Favorites
        if created_listings:
            Favorite.objects.get_or_create(user=buyer1, listing=created_listings[0])
            Favorite.objects.get_or_create(user=buyer1, listing=created_listings[1])
            Favorite.objects.get_or_create(user=buyer2, listing=created_listings[2])

        # Reports
        if created_listings:
            ListingReport.objects.get_or_create(
                listing=created_listings[2],
                reporter=buyer1,
                reason="other",
                defaults={
                    "description": "Dummy report for testing moderation workflow.",
                },
            )

        # Notifications
        Notification.objects.get_or_create(
            user=seller1,
            notification_type="system",
            title="Welcome to QOT",
            message="Your seller account is ready. Start posting quality listings.",
        )

        Notification.objects.get_or_create(
            user=buyer1,
            notification_type="system",
            title="Welcome to QOT",
            message="You can now search, save listings, and chat with sellers.",
        )

        self.stdout.write(self.style.SUCCESS("Dummy data seeded successfully."))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Test login accounts:"))
        self.stdout.write("Admin:  +256700000000 / AdminPass123")
        self.stdout.write("Seller: +256700000001 / StrongPass123")
        self.stdout.write("Seller: +256700000002 / StrongPass123")
        self.stdout.write("Buyer:  +256700000003 / StrongPass123")
        self.stdout.write("Buyer:  +256700000004 / StrongPass123")