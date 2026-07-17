from __future__ import annotations

import re
from typing import Any

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db.models.deletion import ProtectedError


def norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def has_word(text: str, keyword: str) -> bool:
    return f" {norm(keyword)} " in f" {norm(text)} "


def has_any(text: str, keywords: list[str]) -> bool:
    return any(has_word(text, keyword) for keyword in keywords)


def discover_model(possible_names: list[str]):
    for model in apps.get_models():
        if model.__name__ in possible_names:
            return model
    return None


def field_exists(model, name: str) -> bool:
    return any(field.name == name for field in model._meta.fields)


def get_field_type(model, name: str) -> str:
    for field in model._meta.fields:
        if field.name == name:
            return field.get_internal_type()
    return ""


def first_existing_field(model, names: list[str]) -> str | None:
    for name in names:
        if field_exists(model, name):
            return name
    return None


def get_category_label(category: Any) -> str:
    for name in ["name", "title", "label"]:
        if hasattr(category, name):
            return str(getattr(category, name) or "")
    return str(category)


def get_category_slug(category: Any) -> str:
    for name in ["slug", "code", "key"]:
        if hasattr(category, name):
            return str(getattr(category, name) or "")
    return ""


def get_category_parent(category: Any):
    for name in ["parent", "parent_category"]:
        if hasattr(category, name):
            return getattr(category, name)
    return None


def get_category_path(category: Any) -> str:
    names = []
    current = category

    for _ in range(8):
        if not current:
            break
        names.append(get_category_label(current))
        current = get_category_parent(current)

    return " ".join(reversed(names))


def options_value(model, field_name: str | None, options: list[Any]):
    if not field_name:
        return None

    internal_type = get_field_type(model, field_name)

    if internal_type in ["JSONField", "ArrayField"]:
        return options

    return "|".join(str(item) for item in options)


def set_if_exists(payload: dict[str, Any], model, names: list[str], value: Any):
    field = first_existing_field(model, names)
    if field:
        payload[field] = value
    return field


def f(
    key: str,
    label: str,
    type_: str = "text",
    options: list[Any] | None = None,
    placeholder: str = "",
):
    return {
        "key": key,
        "label": label,
        "type": type_,
        "options": options or [],
        "placeholder": placeholder,
    }


LAPTOP_BRANDS = [
    "Apple", "Dell", "HP", "Lenovo", "Asus", "Acer", "Microsoft", "Samsung",
    "Toshiba", "Fujitsu", "MSI", "Razer", "Huawei", "LG", "Alienware", "Other",
]

PHONE_BRANDS = [
    "Apple", "Samsung", "Tecno", "Infinix", "Itel", "Huawei", "Xiaomi",
    "Redmi", "Oppo", "Vivo", "Nokia", "Google", "Sony", "OnePlus", "Realme",
    "Motorola", "Other",
]

CAR_MAKES = [
    "Toyota", "Mercedes-Benz", "BMW", "Audi", "Volkswagen", "Nissan",
    "Subaru", "Honda", "Mazda", "Mitsubishi", "Ford", "Isuzu", "Suzuki",
    "Kia", "Hyundai", "Land Rover", "Range Rover", "Jeep", "Lexus",
    "Daihatsu", "Peugeot", "Renault", "Other",
]

MOTORCYCLE_MAKES = [
    "Bajaj", "TVS", "Honda", "Yamaha", "Suzuki", "Kawasaki", "Hero",
    "Boxer", "Haojue", "Other",
]

APPLIANCE_BRANDS = [
    "Samsung", "LG", "Hisense", "Sony", "TCL", "Nasco", "Philips",
    "Kenwood", "Ramtons", "Midea", "Bruhm", "Von", "Whirlpool", "Other",
]

TV_BRANDS = [
    "Samsung", "LG", "Hisense", "Sony", "TCL", "Skyworth", "Vitron",
    "Vision Plus", "Nasco", "Bruhm", "Other",
]

FASHION_BRANDS = [
    "Nike", "Adidas", "Puma", "Gucci", "Louis Vuitton", "Zara", "H&M",
    "Clarks", "Balenciaga", "New Balance", "Rolex", "Casio", "Other",
]


RULES = [
    {
        "name": "Land",
        "leaf": ["land", "plot", "plots"],
        "filters": [
            f("land_size", "Land Size", "text", placeholder="50x100, 12 decimals, 1 acre..."),
            f("land_unit", "Land Unit", "select", ["Decimals", "Acres", "Hectares", "Square Feet", "Square Metres"]),
            f("title_status", "Title Status", "select", ["Private Mailo", "Freehold", "Leasehold", "Customary", "Agreement", "No Title"]),
            f("land_use", "Land Use", "select", ["Residential", "Commercial", "Agricultural", "Industrial", "Mixed Use"]),
            f("road_access", "Road Access", "select", ["Main Road", "Murram Road", "Feeder Road", "No Road Access"]),
            f("water_available", "Water Available", "boolean"),
            f("electricity_available", "Electricity Available", "boolean"),
            f("fenced", "Fenced", "boolean"),
        ],
    },
    {
        "name": "Houses and Apartments",
        "leaf": ["house", "houses", "apartment", "apartments", "flat", "flats", "villa", "bungalow"],
        "filters": [
            f("property_type", "Property Type", "select", ["House", "Apartment", "Flat", "Villa", "Bungalow", "Mansion", "Duplex"]),
            f("purpose", "Purpose", "select", ["For Rent", "For Sale", "Short Stay"]),
            f("bedrooms", "Bedrooms", "select", ["1", "2", "3", "4", "5", "6+"]),
            f("bathrooms", "Bathrooms", "select", ["1", "2", "3", "4", "5+"]),
            f("furnished", "Furnished", "select", ["Furnished", "Semi-furnished", "Unfurnished"]),
            f("parking", "Parking", "select", ["Yes", "No"]),
            f("compound", "Compound", "select", ["Private Compound", "Shared Compound", "No Compound"]),
            f("security", "Security", "select", ["Wall Fence", "Security Guard", "CCTV", "None"]),
            f("water_available", "Water Available", "boolean"),
            f("electricity_available", "Electricity Available", "boolean"),
        ],
    },
    {
        "name": "Rooms",
        "leaf": ["room", "rooms", "single room", "double room", "studio", "hostel"],
        "filters": [
            f("room_type", "Room Type", "select", ["Single Room", "Double Room", "Studio", "Bedsitter", "Hostel Room"]),
            f("self_contained", "Self Contained", "boolean"),
            f("furnished", "Furnished", "select", ["Furnished", "Semi-furnished", "Unfurnished"]),
            f("bathroom_type", "Bathroom Type", "select", ["Inside", "Outside", "Shared"]),
            f("water_available", "Water Available", "boolean"),
            f("electricity_available", "Electricity Available", "boolean"),
        ],
    },
    {
        "name": "Commercial Property",
        "leaf": ["shop", "office", "warehouse", "commercial", "arcade", "stall"],
        "filters": [
            f("property_type", "Property Type", "select", ["Shop", "Office", "Warehouse", "Stall", "Arcade Space", "Restaurant Space", "Salon Space"]),
            f("purpose", "Purpose", "select", ["For Rent", "For Sale"]),
            f("floor_area", "Floor Area", "text", placeholder="20 sqm, 500 sqft..."),
            f("parking", "Parking", "select", ["Yes", "No"]),
            f("road_access", "Road Access", "select", ["Main Road", "Trading Centre", "Mall/Arcade", "Estate Road"]),
            f("water_available", "Water Available", "boolean"),
            f("electricity_available", "Electricity Available", "boolean"),
        ],
    },
    {
        "name": "Laptops and Computers",
        "leaf": ["laptop", "laptops", "computer", "computers", "desktop", "desktops", "macbook"],
        "filters": [
            f("brand", "Brand", "select", LAPTOP_BRANDS),
            f("model", "Model", "text", placeholder="Latitude 7400, ThinkPad T14, MacBook Air..."),
            f("processor", "Processor", "select", [
                "Intel Core i3", "Intel Core i5", "Intel Core i7", "Intel Core i9",
                "Intel Celeron", "Intel Pentium", "AMD Ryzen 3", "AMD Ryzen 5",
                "AMD Ryzen 7", "AMD Ryzen 9", "Apple M1", "Apple M2", "Apple M3", "Other",
            ]),
            f("ram", "RAM", "select", ["2GB", "4GB", "8GB", "12GB", "16GB", "24GB", "32GB", "64GB", "128GB"]),
            f("storage", "Storage", "select", ["128GB", "256GB", "512GB", "1TB", "2TB", "4TB"]),
            f("storage_type", "Storage Type", "select", ["SSD", "HDD", "SSD + HDD", "eMMC"]),
            f("screen_size", "Screen Size", "select", ["11 inch", "12 inch", "13 inch", "14 inch", "15 inch", "16 inch", "17 inch", "18 inch"]),
            f("graphics", "Graphics", "select", ["Integrated", "NVIDIA", "AMD Radeon", "Apple GPU", "Other"]),
            f("operating_system", "Operating System", "select", ["Windows", "macOS", "Linux", "ChromeOS", "No OS"]),
            f("touch_screen", "Touch Screen", "boolean"),
        ],
    },
    {
        "name": "Phones and Tablets",
        "leaf": ["phone", "phones", "mobile", "smartphone", "tablet", "tablets", "iphone", "ipad"],
        "filters": [
            f("brand", "Brand", "select", PHONE_BRANDS),
            f("model", "Model", "text", placeholder="iPhone 13, Galaxy S22, Tecno Camon..."),
            f("storage", "Storage", "select", ["16GB", "32GB", "64GB", "128GB", "256GB", "512GB", "1TB"]),
            f("ram", "RAM", "select", ["1GB", "2GB", "3GB", "4GB", "6GB", "8GB", "12GB", "16GB"]),
            f("network", "Network", "select", ["2G", "3G", "4G LTE", "5G"]),
            f("sim", "SIM", "select", ["Single SIM", "Dual SIM", "eSIM", "Dual SIM + eSIM"]),
            f("battery_health", "Battery Health", "number", placeholder="85"),
        ],
    },
    {
        "name": "Cars",
        "leaf": ["car", "cars", "vehicle", "vehicles", "suv", "van", "pickup", "truck", "trucks"],
        "filters": [
            f("make", "Make", "select", CAR_MAKES),
            f("model", "Model", "text", placeholder="Harrier, Premio, Forester..."),
            f("year", "Year", "number", placeholder="2015"),
            f("mileage", "Mileage", "number", placeholder="85000"),
            f("fuel", "Fuel Type", "select", ["Petrol", "Diesel", "Hybrid", "Electric"]),
            f("transmission", "Transmission", "select", ["Automatic", "Manual", "Semi-automatic"]),
            f("engine_size", "Engine Size", "select", ["660cc", "1000cc", "1300cc", "1500cc", "1800cc", "2000cc", "2500cc", "3000cc", "3500cc+", "Other"]),
            f("body_type", "Body Type", "select", ["Sedan", "SUV", "Hatchback", "Wagon", "Pickup", "Van", "Truck", "Bus"]),
            f("drive", "Drive", "select", ["2WD", "4WD", "AWD"]),
            f("color", "Color", "select", ["Black", "White", "Silver", "Grey", "Blue", "Red", "Green", "Brown", "Other"]),
        ],
    },
    {
        "name": "Motorcycles",
        "leaf": ["motorcycle", "motorcycles", "bike", "bikes", "boda", "scooter"],
        "filters": [
            f("make", "Make", "select", MOTORCYCLE_MAKES),
            f("model", "Model", "text", placeholder="Boxer, TVS, FZ..."),
            f("year", "Year", "number", placeholder="2020"),
            f("engine_size", "Engine Size", "select", ["50cc", "100cc", "125cc", "150cc", "180cc", "200cc", "250cc", "400cc+", "Other"]),
            f("mileage", "Mileage", "number", placeholder="20000"),
            f("transmission", "Transmission", "select", ["Manual", "Automatic"]),
            f("color", "Color", "select", ["Black", "Red", "Blue", "White", "Silver", "Other"]),
        ],
    },
    {
        "name": "TVs",
        "leaf": ["tv", "television", "televisions"],
        "filters": [
            f("brand", "Brand", "select", TV_BRANDS),
            f("screen_size", "Screen Size", "select", ["24 inch", "32 inch", "40 inch", "43 inch", "50 inch", "55 inch", "65 inch", "75 inch", "85 inch"]),
            f("display_type", "Display Type", "select", ["LED", "OLED", "QLED", "LCD", "Plasma"]),
            f("resolution", "Resolution", "select", ["HD", "Full HD", "2K", "4K UHD", "8K"]),
            f("smart_tv", "Smart TV", "boolean"),
        ],
    },
    {
        "name": "Home Appliances",
        "leaf": ["appliance", "appliances", "fridge", "refrigerator", "cooker", "washing machine", "blender", "microwave", "freezer"],
        "filters": [
            f("brand", "Brand", "select", APPLIANCE_BRANDS),
            f("appliance_type", "Appliance Type", "select", ["Fridge", "Freezer", "Cooker", "Microwave", "Blender", "Washing Machine", "Kettle", "Iron", "Fan", "Air Conditioner", "Other"]),
            f("capacity", "Capacity", "text", placeholder="200L, 7kg, 1.5L..."),
            f("power_source", "Power Source", "select", ["Electric", "Gas", "Solar", "Manual"]),
            f("color", "Color", "select", ["Black", "White", "Silver", "Grey", "Red", "Other"]),
        ],
    },
    {
        "name": "Furniture",
        "leaf": ["furniture", "sofa", "chair", "chairs", "table", "tables", "bed", "beds", "wardrobe"],
        "filters": [
            f("furniture_type", "Furniture Type", "select", ["Sofa", "Bed", "Dining Table", "Chair", "Wardrobe", "TV Stand", "Office Desk", "Cabinet", "Other"]),
            f("material", "Material", "select", ["Wood", "Metal", "Glass", "Plastic", "Leather", "Fabric", "Other"]),
            f("color", "Color", "select", ["Black", "White", "Brown", "Grey", "Blue", "Red", "Other"]),
            f("room", "Room", "select", ["Living Room", "Bedroom", "Office", "Dining Room", "Outdoor"]),
        ],
    },
    {
        "name": "Fashion",
        "leaf": ["fashion", "clothing", "clothes", "shoes", "bags", "watch", "watches", "jewelry", "jewellery"],
        "filters": [
            f("brand", "Brand", "select", FASHION_BRANDS),
            f("gender", "Gender", "select", ["Men", "Women", "Unisex", "Boys", "Girls"]),
            f("item_type", "Item Type", "select", ["Clothes", "Shoes", "Bag", "Watch", "Jewelry", "Belt", "Cap", "Other"]),
            f("size", "Size", "select", ["XS", "S", "M", "L", "XL", "XXL", "XXXL", "EU 36", "EU 37", "EU 38", "EU 39", "EU 40", "EU 41", "EU 42", "EU 43", "EU 44", "EU 45"]),
            f("color", "Color", "select", ["Black", "White", "Blue", "Red", "Green", "Yellow", "Brown", "Grey", "Pink", "Purple", "Other"]),
            f("material", "Material", "select", ["Cotton", "Leather", "Synthetic", "Denim", "Silk", "Wool", "Gold", "Silver", "Stainless Steel", "Other"]),
        ],
    },
    {
        "name": "Jobs",
        "leaf": ["job", "jobs", "career", "vacancy", "vacancies"],
        "filters": [
            f("job_type", "Job Type", "select", ["Full-time", "Part-time", "Contract", "Internship", "Temporary", "Remote"]),
            f("work_mode", "Work Mode", "select", ["On-site", "Remote", "Hybrid"]),
            f("experience_level", "Experience Level", "select", ["Entry Level", "1-2 years", "3-5 years", "5+ years"]),
            f("education_level", "Education Level", "select", ["UCE", "UACE", "Certificate", "Diploma", "Bachelor's Degree", "Master's Degree"]),
            f("salary_type", "Salary Type", "select", ["Monthly", "Weekly", "Daily", "Commission", "Negotiable"]),
            f("company", "Company", "text", placeholder="Company name"),
        ],
    },
    {
        "name": "Services",
        "leaf": ["service", "services", "repair", "professional", "cleaning", "plumbing", "design"],
        "filters": [
            f("service_type", "Service Type", "text", placeholder="Cleaning, repair, design..."),
            f("availability", "Availability", "select", ["Weekdays", "Weekends", "24/7", "By appointment"]),
            f("experience", "Experience", "select", ["Less than 1 year", "1-2 years", "3-5 years", "5+ years"]),
            f("service_location", "Service Location", "select", ["Client Location", "Provider Location", "Online", "Both"]),
        ],
    },
    {
        "name": "Agriculture and Animals",
        "leaf": ["agriculture", "farm", "farming", "animal", "animals", "livestock", "pet", "pets", "goat", "cow", "chicken"],
        "filters": [
            f("item_type", "Item Type", "select", ["Seeds", "Feeds", "Fertilizer", "Farm Tools", "Cattle", "Goats", "Pigs", "Chicken", "Dogs", "Cats", "Fish", "Other"]),
            f("breed", "Breed", "text", placeholder="Breed"),
            f("age", "Age", "text", placeholder="Age"),
            f("gender", "Gender", "select", ["Male", "Female", "Mixed", "Not Applicable"]),
            f("quantity", "Quantity", "number", placeholder="10"),
            f("vaccinated", "Vaccinated", "boolean"),
        ],
    },
    {
        "name": "Books and Office",
        "leaf": ["book", "books", "office", "stationery", "printer"],
        "filters": [
            f("item_type", "Item Type", "select", ["Book", "Textbook", "Novel", "Printer", "Stationery", "Office Furniture", "Other"]),
            f("subject", "Subject", "text", placeholder="Math, Law, Business..."),
            f("author", "Author", "text", placeholder="Author name"),
            f("level", "Level", "select", ["Primary", "Secondary", "University", "Professional", "General"]),
        ],
    },
    {
        "name": "General Electronics",
        "path": ["electronics", "gadgets", "accessories"],
        "filters": [
            f("brand", "Brand", "text", placeholder="Brand name"),
            f("item_type", "Item Type", "text", placeholder="Charger, speaker, router..."),
            f("connectivity", "Connectivity", "select", ["Wired", "Wireless", "Bluetooth", "WiFi", "USB", "Other"]),
        ],
    },
    {
        "name": "General Property",
        "path": ["property", "real estate"],
        "filters": [
            f("property_type", "Property Type", "select", ["House", "Apartment", "Room", "Shop", "Office", "Warehouse", "Land", "Other"]),
            f("purpose", "Purpose", "select", ["For Rent", "For Sale", "Short Stay"]),
            f("location_type", "Location Type", "select", ["Town", "Suburb", "Trading Centre", "Village", "Main Road"]),
        ],
    },
]


def choose_specs(category) -> tuple[str, list[dict[str, Any]]]:
    leaf_text = norm(f"{get_category_label(category)} {get_category_slug(category)}")
    path_text = norm(f"{get_category_path(category)} {get_category_slug(category)}")

    for rule in RULES:
        if has_any(leaf_text, rule.get("leaf", [])):
            return rule["name"], rule["filters"]

    for rule in RULES:
        if has_any(path_text, rule.get("path", [])):
            return rule["name"], rule["filters"]

    return (
        "General",
        [
            f("item_type", "Item Type", "text", placeholder="Type or style"),
        ],
    )


def create_or_update_filter(FilterModel, category, spec: dict[str, Any], order: int):
    category_field = first_existing_field(
        FilterModel,
        ["category", "listing_category", "parent_category"],
    )

    key_field = first_existing_field(
        FilterModel,
        ["key", "slug", "field_slug", "parameter", "code", "name"],
    )

    if not category_field or not key_field:
        raise RuntimeError(
            "Could not find category/key fields on the category filter model."
        )

    lookup = {
        category_field: category,
        key_field: spec["key"],
    }

    payload = {}

    set_if_exists(payload, FilterModel, ["label", "display_name", "title"], spec["label"])

    if key_field != "name":
        set_if_exists(payload, FilterModel, ["name"], spec["label"])

    set_if_exists(
        payload,
        FilterModel,
        ["input_type", "field_type", "type"],
        spec.get("type", "text"),
    )

    set_if_exists(payload, FilterModel, ["placeholder"], spec.get("placeholder", ""))

    options_field = first_existing_field(
        FilterModel,
        ["options", "choices", "values", "allowed_values"],
    )

    if options_field:
        payload[options_field] = options_value(
            FilterModel,
            options_field,
            spec.get("options", []),
        )

    set_if_exists(payload, FilterModel, ["sort_order", "order", "position"], order)
    set_if_exists(payload, FilterModel, ["is_active", "active"], True)
    set_if_exists(payload, FilterModel, ["filterable", "is_filterable"], True)

    obj, created = FilterModel.objects.update_or_create(
        **lookup,
        defaults=payload,
    )

    return obj, created


class Command(BaseCommand):
    help = "Seed QOT category-specific filters for categories and subcategories."

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete-stale",
            action="store_true",
            help="Delete old filters that are not in the revised seed for each category.",
        )

    def handle(self, *args, **options):
        Category = discover_model(["Category", "ListingCategory"])
        FilterModel = discover_model(
            [
                "CategoryFilter",
                "ListingCategoryFilter",
                "FilterField",
                "ListingFilter",
                "CategoryAttribute",
            ]
        )

        if Category is None:
            self.stderr.write(self.style.ERROR("Could not find Category model."))
            return

        if FilterModel is None:
            self.stderr.write(
                self.style.ERROR(
                    "Could not find CategoryFilter model. Paste your category models.py so we can match it."
                )
            )
            return

        categories = list(Category.objects.all())

        if not categories:
            self.stderr.write(self.style.ERROR("No categories found. Seed categories first."))
            return

        category_field = first_existing_field(
            FilterModel,
            ["category", "listing_category", "parent_category"],
        )
        key_field = first_existing_field(
            FilterModel,
            ["key", "slug", "field_slug", "parameter", "code", "name"],
        )

        created_count = 0
        updated_count = 0
        deleted_count = 0

        for category in categories:
            rule_name, specs = choose_specs(category)
            valid_keys = [spec["key"] for spec in specs]

            for index, spec in enumerate(specs, start=1):
                _, created = create_or_update_filter(FilterModel, category, spec, index)

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            if options["delete_stale"] and category_field and key_field:
                stale_qs = FilterModel.objects.filter(**{category_field: category}).exclude(
                    **{f"{key_field}__in": valid_keys}
                )

                stale_count = stale_qs.count()

                deactivate_payload = {}

                for bool_field in ["is_active", "active", "filterable", "is_filterable"]:
                    if field_exists(FilterModel, bool_field):
                        deactivate_payload[bool_field] = False

                if deactivate_payload:
                    stale_qs.update(**deactivate_payload)
                    deleted_count += stale_count
                else:
                    try:
                        deleted, _ = stale_qs.delete()
                        deleted_count += deleted
                    except ProtectedError:
                        self.stdout.write(
                            self.style.WARNING(
                                f"{get_category_path(category)}: skipped {stale_count} protected stale filters"
                            )
                        )






            self.stdout.write(
                self.style.SUCCESS(
                    f"{get_category_path(category)} -> {rule_name}: seeded {len(specs)} filters"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created {created_count}, updated {updated_count}, deactivated/deleted {deleted_count} stale filters."
            )
        )