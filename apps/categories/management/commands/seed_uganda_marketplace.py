from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.categories.models import Category
from apps.locations.models import Region, City

CATEGORIES = [
    {
        "name": "Electronics",
        "children": [
            "Mobile Phones",
            "Laptops & Computers",
            "Tablets",
            "TVs",
            "Cameras",
            "Audio & Speakers",
            "Computer Accessories",
            "Gaming Consoles",
            "Smart Watches",
            "Printers & Scanners",
        ],
    },
    {
        "name": "Vehicles",
        "children": [
            "Cars",
            "Motorcycles",
            "Trucks",
            "Buses",
            "Car Parts",
            "Motorcycle Parts",
            "Tyres & Wheels",
            "Vehicle Services",
            "Boats",
            "Heavy Equipment",
        ],
    },
    {
        "name": "Property",
        "children": [
            "Houses for Sale",
            "Houses for Rent",
            "Apartments for Rent",
            "Land for Sale",
            "Commercial Property",
            "Shops & Offices",
            "Short Stay Rentals",
            "Hostels & Rentals",
        ],
    },
    {
        "name": "Fashion",
        "children": [
            "Men's Clothing",
            "Women's Clothing",
            "Shoes",
            "Bags",
            "Watches",
            "Jewellery",
            "Children's Clothing",
            "Wedding Wear",
            "Uniforms",
        ],
    },
    {
        "name": "Home & Furniture",
        "children": [
            "Sofas",
            "Beds & Mattresses",
            "Tables & Chairs",
            "Wardrobes",
            "Kitchen Items",
            "Home Decor",
            "Lighting",
            "Curtains & Carpets",
            "Appliances",
        ],
    },
    {
        "name": "Jobs",
        "children": [
            "Accounting & Finance Jobs",
            "Sales & Marketing Jobs",
            "Teaching Jobs",
            "Driver Jobs",
            "Hotel & Restaurant Jobs",
            "Office Jobs",
            "IT Jobs",
            "Security Jobs",
            "Part-time Jobs",
        ],
    },
    {
        "name": "Services",
        "children": [
            "Computer Repair",
            "Phone Repair",
            "Graphic Design",
            "Printing Services",
            "Cleaning Services",
            "Construction Services",
            "Transport Services",
            "Event Services",
            "Photography & Video",
            "Legal Services",
            "Business Services",
            "Beauty Services",
        ],
    },
    {
        "name": "Agriculture",
        "children": [
            "Farm Animals",
            "Poultry",
            "Seeds",
            "Fertilizers",
            "Farm Tools",
            "Animal Feeds",
            "Fresh Produce",
            "Agricultural Land",
        ],
    },
    {
        "name": "Health & Beauty",
        "children": [
            "Skin Care",
            "Hair Products",
            "Makeup",
            "Perfumes",
            "Salon Equipment",
            "Fitness Equipment",
            "Personal Care",
        ],
    },
    {
        "name": "Baby & Kids",
        "children": [
            "Baby Clothes",
            "Baby Shoes",
            "Toys",
            "Baby Furniture",
            "School Items",
            "Kids Accessories",
        ],
    },
    {
        "name": "Sports & Hobbies",
        "children": [
            "Gym Equipment",
            "Bicycles",
            "Sports Wear",
            "Musical Instruments",
            "Books",
            "Art & Crafts",
        ],
    },
    {
        "name": "Pets",
        "children": [
            "Dogs",
            "Cats",
            "Birds",
            "Pet Food",
            "Pet Accessories",
            "Veterinary Services",
        ],
    },
]


UGANDA_LOCATIONS = {
    "Central": [
        "Kampala",
        "Wakiso",
        "Mukono",
        "Masaka",
        "Mityana",
        "Luwero",
        "Nakasongola",
        "Kayunga",
        "Buikwe",
        "Buvuma",
        "Kalangala",
        "Mpigi",
        "Butambala",
        "Gomba",
        "Sembabule",
        "Bukomansimbi",
        "Kalungu",
        "Lwengo",
        "Kyotera",
        "Rakai",
        "Lyantonde",
        "Mubende",
        "Kasanda",
        "Kiboga",
        "Kyankwanzi",
        "Nakaseke",
    ],
    "Eastern": [
        "Jinja",
        "Mbale",
        "Soroti",
        "Tororo",
        "Iganga",
        "Busia",
        "Bugiri",
        "Mayuge",
        "Kamuli",
        "Buyende",
        "Kaliro",
        "Luuka",
        "Namutumba",
        "Butaleja",
        "Budaka",
        "Kibuku",
        "Pallisa",
        "Kumi",
        "Ngora",
        "Serere",
        "Kaberamaido",
        "Bukedea",
        "Kapchorwa",
        "Kween",
        "Bukwo",
        "Sironko",
        "Bulambuli",
        "Bududa",
        "Manafwa",
        "Namisindwa",
        "Namayingo",
    ],
    "Northern": [
        "Gulu",
        "Lira",
        "Arua",
        "Kitgum",
        "Pader",
        "Agago",
        "Lamwo",
        "Nwoya",
        "Amuru",
        "Omoro",
        "Oyam",
        "Apac",
        "Kole",
        "Dokolo",
        "Alebtong",
        "Otuke",
        "Amolatar",
        "Kwania",
        "Nebbi",
        "Zombo",
        "Pakwach",
        "Moyo",
        "Obongi",
        "Adjumani",
        "Yumbe",
        "Koboko",
        "Maracha",
        "Terego",
        "Madi-Okollo",
        "Kaabong",
        "Kotido",
        "Moroto",
        "Nakapiripirit",
        "Napak",
        "Amudat",
        "Nabilatuk",
        "Karenga",
    ],
    "Western": [
        "Mbarara",
        "Fort Portal",
        "Hoima",
        "Masindi",
        "Buliisa",
        "Kiryandongo",
        "Kikuube",
        "Kakumiro",
        "Kagadi",
        "Kibaale",
        "Kyenjojo",
        "Kyegegwa",
        "Kabarole",
        "Bunyangabu",
        "Kasese",
        "Bundibugyo",
        "Ntoroko",
        "Kamwenge",
        "Ibanda",
        "Kiruhura",
        "Isingiro",
        "Ntungamo",
        "Rukungiri",
        "Kanungu",
        "Kabale",
        "Rubanda",
        "Rukiga",
        "Kisoro",
        "Bushenyi",
        "Sheema",
        "Buhweju",
        "Rubirizi",
        "Mitooma",
    ],
}


class Command(BaseCommand):
    help = "Seed QOT marketplace categories and Uganda locations"

    def handle(self, *args, **options):
        self.seed_categories()
        self.seed_locations()

        self.stdout.write(
            self.style.SUCCESS("Successfully seeded Uganda marketplace data.")
        )

    def seed_categories(self):
        self.stdout.write("Seeding categories...")

        sort_order = 1

        for category in CATEGORIES:
            parent_slug = slugify(category["name"])

            parent, created = Category.objects.get_or_create(
                slug=parent_slug,
                defaults={
                    "name": category["name"],
                    "parent": None,
                    "icon": category.get("icon", ""),
                    "is_active": True,
                    "sort_order": sort_order,
                },
            )

            update_fields = []

            if parent.name != category["name"]:
                parent.name = category["name"]
                update_fields.append("name")

            if parent.parent_id is not None:
                parent.parent = None
                update_fields.append("parent")

            if parent.is_active is not True:
                parent.is_active = True
                update_fields.append("is_active")

            if parent.sort_order != sort_order:
                parent.sort_order = sort_order
                update_fields.append("sort_order")

            if update_fields:
                parent.save(update_fields=update_fields)

            child_sort = 1

            for child_name in category["children"]:
                child_slug = slugify(child_name)

                child, child_created = Category.objects.get_or_create(
                    slug=child_slug,
                    defaults={
                        "name": child_name,
                        "parent": parent,
                        "icon": "",
                        "is_active": True,
                        "sort_order": child_sort,
                    },
                )

                child_update_fields = []

                if child.name != child_name:
                    child.name = child_name
                    child_update_fields.append("name")

                if child.parent_id != parent.id:
                    child.parent = parent
                    child_update_fields.append("parent")

                if child.is_active is not True:
                    child.is_active = True
                    child_update_fields.append("is_active")

                if child.sort_order != child_sort:
                    child.sort_order = child_sort
                    child_update_fields.append("sort_order")

                if child_update_fields:
                    child.save(update_fields=child_update_fields)

                child_sort += 1

            sort_order += 1

        self.stdout.write(self.style.SUCCESS("Categories seeded."))

    def seed_locations(self):
        self.stdout.write("Seeding Uganda locations...")

        region_sort = 1

        for region_name, cities in UGANDA_LOCATIONS.items():
            region, created = Region.objects.get_or_create(
                slug=slugify(region_name),
                defaults={
                    "name": region_name,
                    "is_active": True,
                },
            )

            update_fields = []

            if region.name != region_name:
                region.name = region_name
                update_fields.append("name")

            if region.is_active is not True:
                region.is_active = True
                update_fields.append("is_active")

            if update_fields:
                region.save(update_fields=update_fields)

            for city_name in cities:
                city_slug = slugify(city_name)

                city, city_created = City.objects.get_or_create(
                    region=region,
                    slug=city_slug,
                    defaults={
                        "name": city_name,
                        "is_active": True,
                    },
                )

                city_update_fields = []

                if city.name != city_name:
                    city.name = city_name
                    city_update_fields.append("name")

                if city.is_active is not True:
                    city.is_active = True
                    city_update_fields.append("is_active")

                if city_update_fields:
                    city.save(update_fields=city_update_fields)

            region_sort += 1

        self.stdout.write(self.style.SUCCESS("Uganda locations seeded."))