from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from apps.accounts.models import User
from apps.categories.models import Category
from apps.locations.models import Region, City
from apps.listings.models import Listing


class Command(BaseCommand):
    help = "Seed QOT dummy data for local development"

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Seeding QOT dummy data..."))

        def has_field(model, field_name):
            return any(field.name == field_name for field in model._meta.fields)

        def unwrap(value):
            """
            Prevent errors like:
            (<Category: Phones>,)

            This happens when a variable accidentally has a trailing comma.
            """
            if isinstance(value, tuple):
                return value[0]
            return value

        def save_if_changed(obj, fields):
            update_fields = []

            for field, value in fields.items():
                if has_field(obj.__class__, field):
                    setattr(obj, field, value)
                    update_fields.append(field)

            if update_fields:
                obj.save(update_fields=update_fields)

            return obj
        

        def get_region(name, slug):
            region = Region.objects.filter(slug=slug).order_by("id").first()

            if not region:
                region = Region.objects.create(
                    name=name,
                    slug=slug,
                )

            save_if_changed(
                region,
                {
                    "name": name,
                    "slug": slug,
                    "is_active": True,
                },
            )

            return region


        def get_city(name, slug, region):
            """
            City has a unique constraint on:
            region + slug

            So we must search using both region and slug,
            not slug alone.
            """

            city = City.objects.filter(
                region=region,
                slug=slug,
            ).order_by("id").first()

            if not city:
                city = City.objects.filter(
                    region=region,
                    name__iexact=name,
                ).order_by("id").first()

            if not city:
                city = City.objects.create(
                    name=name,
                    slug=slug,
                    region=region,
                )
                return city

            city.name = name
            city.region = region

            # Only update slug if it will not violate the unique constraint.
            slug_exists = City.objects.filter(
                region=region,
                slug=slug,
            ).exclude(id=city.id).exists()

            if not slug_exists:
                city.slug = slug

            update_fields = ["name", "region"]

            if not slug_exists:
                update_fields.append("slug")

            if has_field(City, "is_active"):
                city.is_active = True
                update_fields.append("is_active")

            city.save(update_fields=update_fields)

            return city

        def get_category(name, slug, parent=None, sort_order=0):
            category = Category.objects.filter(slug=slug).order_by("id").first()

            if not category:
                category = Category.objects.create(
                    name=name,
                    slug=slug,
                    parent=parent,
                    sort_order=sort_order,
                )

            save_if_changed(
                category,
                {
                    "name": name,
                    "slug": slug,
                    "parent": parent,
                    "sort_order": sort_order,
                    "is_active": True,
                },
            )

            return category


        def get_user(phone, email, full_name, password="StrongPass123"):
            user = User.objects.filter(phone=phone).first()

            if user:
                user.email = email
                user.full_name = full_name
                user.is_active = True
                user.is_verified = True
                user.is_banned = False
                user.save(
                    update_fields=[
                        "email",
                        "full_name",
                        "is_active",
                        "is_verified",
                        "is_banned",
                        "updated_at",
                    ]
                )
                return user

            user = User.objects.create_user(
                phone=phone,
                email=email,
                full_name=full_name,
                password=password,
            )

            user.is_active = True
            user.is_verified = True
            user.is_banned = False
            user.save(
                update_fields=[
                    "is_active",
                    "is_verified",
                    "is_banned",
                ]
            )

            return user

        def get_listing(item):
            seller = unwrap(item["seller"])
            category = unwrap(item["category"])
            city = unwrap(item["city"])

            existing_listing = Listing.objects.filter(
                seller=seller,
                title=item["title"],
            ).first()

            if existing_listing:
                listing = existing_listing

                listing.category = category
                listing.city = city
                listing.description = item["description"]
                listing.price = item["price"]
                listing.currency = item.get("currency", "UGX")
                listing.condition = item.get(
                    "condition",
                    getattr(Listing, "CONDITION_USED", "used"),
                )
                listing.status = item.get(
                    "status",
                    getattr(Listing, "STATUS_ACTIVE", "active"),
                )
                listing.is_negotiable = item.get("is_negotiable", True)
                listing.expires_at = item.get("expires_at")

                if has_field(Listing, "is_featured"):
                    listing.is_featured = item.get("is_featured", False)

                if has_field(Listing, "featured_until"):
                    listing.featured_until = item.get("featured_until")

                update_fields = [
                    "category",
                    "city",
                    "description",
                    "price",
                    "currency",
                    "condition",
                    "status",
                    "is_negotiable",
                    "expires_at",
                    "updated_at",
                ]

                if has_field(Listing, "is_featured"):
                    update_fields.append("is_featured")

                if has_field(Listing, "featured_until"):
                    update_fields.append("featured_until")

                listing.save(update_fields=update_fields)

                return listing, False

            listing = Listing.objects.create(
                seller=seller,
                category=category,
                city=city,
                title=item["title"],
                description=item["description"],
                price=item["price"],
                currency=item.get("currency", "UGX"),
                condition=item.get(
                    "condition",
                    getattr(Listing, "CONDITION_USED", "used"),
                ),
                status=item.get(
                    "status",
                    getattr(Listing, "STATUS_ACTIVE", "active"),
                ),
                is_negotiable=item.get("is_negotiable", True),
                expires_at=item.get("expires_at"),
            )

            if has_field(Listing, "slug"):
                listing.slug = f"{slugify(listing.title)}-{listing.id}"

            if has_field(Listing, "is_featured"):
                listing.is_featured = item.get("is_featured", False)

            if has_field(Listing, "featured_until"):
                listing.featured_until = item.get("featured_until")

            update_fields = []

            if has_field(Listing, "slug"):
                update_fields.append("slug")

            if has_field(Listing, "is_featured"):
                update_fields.append("is_featured")

            if has_field(Listing, "featured_until"):
                update_fields.append("featured_until")

            if update_fields:
                listing.save(update_fields=update_fields)

            return listing, True

        # -------------------------------------------------
        # Regions
        # -------------------------------------------------

        central = get_region("Central Region", "central-region")
        eastern = get_region("Eastern Region", "eastern-region")
        western = get_region("Western Region", "western-region")
        northern = get_region("Northern Region", "northern-region")

        # -------------------------------------------------
        # Cities
        # -------------------------------------------------

        kampala = get_city("Kampala", "kampala", central)
        wakiso = get_city("Wakiso", "wakiso", central)
        mukono = get_city("Mukono", "mukono", central)
        entebbe = get_city("Entebbe", "entebbe", central)

        jinja = get_city("Jinja", "jinja", eastern)
        mbale = get_city("Mbale", "mbale", eastern)

        mbarara = get_city("Mbarara", "mbarara", western)
        fort_portal = get_city("Fort Portal", "fort-portal", western)

        gulu = get_city("Gulu", "gulu", northern)
        lira = get_city("Lira", "lira", northern)

        # -------------------------------------------------
        # Categories
        # -------------------------------------------------

        vehicles = get_category("Vehicles", "vehicles", sort_order=1)
        cars = get_category("Cars", "cars", parent=vehicles, sort_order=1)
        motorcycles = get_category(
            "Motorcycles",
            "motorcycles",
            parent=vehicles,
            sort_order=2,
        )
        spare_parts = get_category(
            "Vehicle Spare Parts",
            "vehicle-spare-parts",
            parent=vehicles,
            sort_order=3,
        )

        phones_tablets = get_category(
            "Phones & Tablets",
            "phones-tablets",
            sort_order=2,
        )
        phones = get_category(
            "Phones",
            "phones",
            parent=phones_tablets,
            sort_order=1,
        )
        tablets = get_category(
            "Tablets",
            "tablets",
            parent=phones_tablets,
            sort_order=2,
        )
        phone_accessories = get_category(
            "Phone Accessories",
            "phone-accessories",
            parent=phones_tablets,
            sort_order=3,
        )

        electronics = get_category("Electronics", "electronics", sort_order=3)
        laptops = get_category(
            "Laptops",
            "laptops",
            parent=electronics,
            sort_order=1,
        )
        desktops = get_category(
            "Desktop Computers",
            "desktop-computers",
            parent=electronics,
            sort_order=2,
        )
        tvs = get_category(
            "TVs",
            "tvs",
            parent=electronics,
            sort_order=3,
        )

        property_category = get_category("Property", "property", sort_order=4)
        houses = get_category(
            "Houses",
            "houses",
            parent=property_category,
            sort_order=1,
        )
        land = get_category(
            "Land",
            "land",
            parent=property_category,
            sort_order=2,
        )
        rentals = get_category(
            "Rentals",
            "rentals",
            parent=property_category,
            sort_order=3,
        )

        fashion = get_category("Fashion", "fashion", sort_order=5)
        clothes = get_category(
            "Clothes",
            "clothes",
            parent=fashion,
            sort_order=1,
        )
        shoes = get_category(
            "Shoes",
            "shoes",
            parent=fashion,
            sort_order=2,
        )
        bags = get_category(
            "Bags",
            "bags",
            parent=fashion,
            sort_order=3,
        )

        home_garden = get_category("Home & Garden", "home-garden", sort_order=6)
        furniture = get_category(
            "Furniture",
            "furniture",
            parent=home_garden,
            sort_order=1,
        )
        appliances = get_category(
            "Appliances",
            "appliances",
            parent=home_garden,
            sort_order=2,
        )

        jobs = get_category("Jobs", "jobs", sort_order=7)
        services = get_category("Services", "services", sort_order=8)

        # -------------------------------------------------
        # Users
        # -------------------------------------------------

        seller_1 = get_user(
            phone="+256700000101",
            email="seller101@example.com",
            full_name="Test Seller One",
        )

        seller_2 = get_user(
            phone="+256700000102",
            email="seller102@example.com",
            full_name="Test Seller Two",
        )

        buyer_1 = get_user(
            phone="+256700000103",
            email="buyer103@example.com",
            full_name="Test Buyer One",
        )

        admin_user = get_user(
            phone="+256700000999",
            email="admin999@example.com",
            full_name="QOT Admin",
        )

        admin_user.role = getattr(User, "ROLE_ADMIN", "admin")
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.is_verified = True
        admin_user.save(
            update_fields=[
                "role",
                "is_staff",
                "is_superuser",
                "is_verified",
                "updated_at",
            ]
        )

        # -------------------------------------------------
        # Listings
        # -------------------------------------------------

        active_status = getattr(Listing, "STATUS_ACTIVE", "active")
        pending_status = getattr(Listing, "STATUS_PENDING", "pending")
        sold_status = getattr(Listing, "STATUS_SOLD", "sold")

        used_condition = getattr(Listing, "CONDITION_USED", "used")
        new_condition = getattr(Listing, "CONDITION_NEW", "new")

        now = timezone.now()

        listings = [
            {
                "seller": seller_1,
                "category": cars,
                "city": kampala,
                "title": "Toyota Premio 2012",
                "description": "Clean Toyota Premio in good condition with nice interior.",
                "price": Decimal("25000000"),
                "currency": "UGX",
                "condition": used_condition,
                "status": active_status,
                "is_negotiable": True,
                "expires_at": now + timedelta(days=30),
                "is_featured": True,
                "featured_until": now + timedelta(days=7),
            },
            {
                "seller": seller_1,
                "category": cars,
                "city": wakiso,
                "title": "Toyota Harrier 2015",
                "description": "Toyota Harrier with clean body, good tyres, and excellent engine.",
                "price": Decimal("58000000"),
                "currency": "UGX",
                "condition": used_condition,
                "status": active_status,
                "is_negotiable": True,
                "expires_at": now + timedelta(days=30),
            },
            {
                "seller": seller_2,
                "category": motorcycles,
                "city": mukono,
                "title": "Bajaj Boxer Motorcycle",
                "description": "Reliable Bajaj Boxer suitable for business and personal transport.",
                "price": Decimal("4200000"),
                "currency": "UGX",
                "condition": used_condition,
                "status": active_status,
                "is_negotiable": True,
                "expires_at": now + timedelta(days=30),
            },
            {
                "seller": seller_1,
                "category": phones,
                "city": kampala,
                "title": "iPhone 13 Pro Max",
                "description": "Original iPhone 13 Pro Max, clean condition, strong battery.",
                "price": Decimal("2800000"),
                "currency": "UGX",
                "condition": used_condition,
                "status": active_status,
                "is_negotiable": True,
                "expires_at": now + timedelta(days=30),
                "is_featured": True,
                "featured_until": now + timedelta(days=5),
            },
            {
                "seller": seller_2,
                "category": phones,
                "city": jinja,
                "title": "Samsung Galaxy S22 Ultra",
                "description": "Samsung Galaxy S22 Ultra with good camera, clean screen, and box.",
                "price": Decimal("2100000"),
                "currency": "UGX",
                "condition": used_condition,
                "status": active_status,
                "is_negotiable": True,
                "expires_at": now + timedelta(days=30),
            },
            {
                "seller": seller_1,
                "category": tablets,
                "city": entebbe,
                "title": "iPad Pro 11 Inch",
                "description": "iPad Pro 11 inch, very clean, good for work, design, and study.",
                "price": Decimal("2200000"),
                "currency": "UGX",
                "condition": used_condition,
                "status": active_status,
                "is_negotiable": True,
                "expires_at": now + timedelta(days=30),
            },
            {
                "seller": seller_1,
                "category": laptops,
                "city": kampala,
                "title": "HP EliteBook 840 G6",
                "description": "Core i5, 8GB RAM, 256GB SSD, clean business laptop.",
                "price": Decimal("1450000"),
                "currency": "UGX",
                "condition": used_condition,
                "status": active_status,
                "is_negotiable": True,
                "expires_at": now + timedelta(days=30),
            },
            {
                "seller": seller_2,
                "category": laptops,
                "city": wakiso,
                "title": "Dell XPS 13 Core i7",
                "description": "Dell XPS 13, Core i7, 16GB RAM, 512GB SSD, premium design.",
                "price": Decimal("2500000"),
                "currency": "UGX",
                "condition": used_condition,
                "status": active_status,
                "is_negotiable": True,
                "expires_at": now + timedelta(days=30),
                "is_featured": True,
                "featured_until": now + timedelta(days=10),
            },
            {
                "seller": seller_2,
                "category": desktops,
                "city": mbarara,
                "title": "Gaming Desktop PC",
                "description": "Powerful gaming desktop with dedicated graphics and SSD storage.",
                "price": Decimal("3500000"),
                "currency": "UGX",
                "condition": used_condition,
                "status": active_status,
                "is_negotiable": True,
                "expires_at": now + timedelta(days=30),
            },
            {
                "seller": seller_1,
                "category": tvs,
                "city": mbale,
                "title": "Samsung 55 Inch Smart TV",
                "description": "Samsung smart TV with clear display and YouTube/Netflix support.",
                "price": Decimal("1800000"),
                "currency": "UGX",
                "condition": used_condition,
                "status": active_status,
                "is_negotiable": True,
                "expires_at": now + timedelta(days=30),
            },
            {
                "seller": seller_2,
                "category": houses,
                "city": kampala,
                "title": "House for Sale in Najjera",
                "description": "Beautiful family house with spacious compound and good neighborhood.",
                "price": Decimal("350000000"),
                "currency": "UGX",
                "condition": used_condition,
                "status": active_status,
                "is_negotiable": True,
                "expires_at": now + timedelta(days=30),
            },
            {
                "seller": seller_1,
                "category": land,
                "city": mukono,
                "title": "Land for Sale in Mukono",
                "description": "50 by 100 plot near the main road, suitable for residential use.",
                "price": Decimal("35000000"),
                "currency": "UGX",
                "condition": used_condition,
                "status": active_status,
                "is_negotiable": True,
                "expires_at": now + timedelta(days=30),
            },
            {
                "seller": seller_2,
                "category": rentals,
                "city": kampala,
                "title": "Two Bedroom Apartment for Rent",
                "description": "Modern two bedroom apartment with parking and security.",
                "price": Decimal("1200000"),
                "currency": "UGX",
                "condition": used_condition,
                "status": active_status,
                "is_negotiable": False,
                "expires_at": now + timedelta(days=30),
            },
            {
                "seller": seller_1,
                "category": furniture,
                "city": wakiso,
                "title": "Modern Sofa Set",
                "description": "Comfortable sofa set suitable for sitting room or office reception.",
                "price": Decimal("950000"),
                "currency": "UGX",
                "condition": used_condition,
                "status": active_status,
                "is_negotiable": True,
                "expires_at": now + timedelta(days=30),
            },
            {
                "seller": seller_2,
                "category": appliances,
                "city": gulu,
                "title": "LG Double Door Fridge",
                "description": "LG fridge in very good condition with strong cooling system.",
                "price": Decimal("1300000"),
                "currency": "UGX",
                "condition": used_condition,
                "status": active_status,
                "is_negotiable": True,
                "expires_at": now + timedelta(days=30),
            },
            {
                "seller": seller_1,
                "category": shoes,
                "city": lira,
                "title": "Original Nike Sneakers",
                "description": "Original Nike sneakers, comfortable and stylish.",
                "price": Decimal("180000"),
                "currency": "UGX",
                "condition": new_condition,
                "status": active_status,
                "is_negotiable": True,
                "expires_at": now + timedelta(days=30),
            },
            {
                "seller": seller_2,
                "category": clothes,
                "city": fort_portal,
                "title": "Men's Casual Shirts",
                "description": "Quality casual shirts available in different sizes.",
                "price": Decimal("45000"),
                "currency": "UGX",
                "condition": new_condition,
                "status": active_status,
                "is_negotiable": False,
                "expires_at": now + timedelta(days=30),
            },
            {
                "seller": seller_1,
                "category": services,
                "city": kampala,
                "title": "Laptop Repair Services",
                "description": "Professional laptop repair, software installation, and SSD upgrades.",
                "price": Decimal("50000"),
                "currency": "UGX",
                "condition": new_condition,
                "status": active_status,
                "is_negotiable": True,
                "expires_at": now + timedelta(days=30),
            },
            {
                "seller": seller_2,
                "category": jobs,
                "city": kampala,
                "title": "Sales Assistant Needed",
                "description": "We need a sales assistant for a busy electronics shop in Kampala.",
                "price": Decimal("0"),
                "currency": "UGX",
                "condition": new_condition,
                "status": active_status,
                "is_negotiable": False,
                "expires_at": now + timedelta(days=30),
            },
            {
                "seller": seller_1,
                "category": phones,
                "city": kampala,
                "title": "Pending Test Phone Listing",
                "description": "This listing is intentionally pending for admin approval testing.",
                "price": Decimal("850000"),
                "currency": "UGX",
                "condition": used_condition,
                "status": pending_status,
                "is_negotiable": True,
                "expires_at": now + timedelta(days=30),
            },
            {
                "seller": seller_2,
                "category": cars,
                "city": wakiso,
                "title": "Sold Test Car Listing",
                "description": "This listing is intentionally sold for status testing.",
                "price": Decimal("15000000"),
                "currency": "UGX",
                "condition": used_condition,
                "status": sold_status,
                "is_negotiable": True,
                "expires_at": now + timedelta(days=30),
            },
        ]

        created_count = 0
        updated_count = 0

        for item in listings:
            listing, created = get_listing(item)

            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete. Created {created_count} listing(s), updated {updated_count} listing(s)."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Test users:"
            )
        )

        self.stdout.write(
            "Seller 1: +256700000101 / StrongPass123"
        )
        self.stdout.write(
            "Seller 2: +256700000102 / StrongPass123"
        )
        self.stdout.write(
            "Buyer:    +256700000103 / StrongPass123"
        )
        self.stdout.write(
            "Admin:    +256700000999 / StrongPass123"
        )