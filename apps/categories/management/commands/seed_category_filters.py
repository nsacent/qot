from __future__ import annotations

import re
from typing import Any

from django.apps import apps
from django.core.management.base import BaseCommand


def norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


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

    for _ in range(6):
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

    set_if_exists(
        payload,
        FilterModel,
        ["label", "display_name", "title"],
        spec["label"],
    )

    if key_field != "name":
        set_if_exists(payload, FilterModel, ["name"], spec["label"])

    set_if_exists(
        payload,
        FilterModel,
        ["input_type", "field_type", "type"],
        spec.get("type", "text"),
    )

    set_if_exists(
        payload,
        FilterModel,
        ["placeholder"],
        spec.get("placeholder", ""),
    )

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


COMMON = [
    f("brand", "Brand", "text", placeholder="Toyota, Apple, HP..."),
    f("model", "Model", "text", placeholder="Model name or number"),
]

FILTER_GROUPS = [
    {
        "match": ["electronics", "computer", "laptop", "desktop"],
        "filters": [
            f("brand", "Brand", "select", ["Apple", "Dell", "HP", "Lenovo", "Acer", "Asus", "Samsung", "Microsoft", "Toshiba", "Other"]),
            f("processor", "Processor", "select", ["Intel Core i3", "Intel Core i5", "Intel Core i7", "Intel Core i9", "AMD Ryzen 3", "AMD Ryzen 5", "AMD Ryzen 7", "Apple M1", "Apple M2", "Apple M3", "Other"]),
            f("ram", "RAM", "select", ["4GB", "8GB", "12GB", "16GB", "24GB", "32GB", "64GB"]),
            f("storage", "Storage", "select", ["128GB SSD", "256GB SSD", "512GB SSD", "1TB SSD", "2TB SSD", "500GB HDD", "1TB HDD"]),
            f("screen_size", "Screen Size", "select", ["11 inch", "12 inch", "13 inch", "14 inch", "15 inch", "16 inch", "17 inch"]),
            f("graphics", "Graphics", "select", ["Integrated", "NVIDIA", "AMD Radeon", "Apple GPU", "Other"]),
            f("operating_system", "Operating System", "select", ["Windows", "macOS", "Linux", "ChromeOS", "No OS"]),
        ],
    },
    {
        "match": ["phone", "mobile", "tablet"],
        "filters": [
            f("brand", "Brand", "select", ["Apple", "Samsung", "Tecno", "Infinix", "Itel", "Huawei", "Xiaomi", "Oppo", "Vivo", "Nokia", "Google", "Other"]),
            f("storage", "Storage", "select", ["16GB", "32GB", "64GB", "128GB", "256GB", "512GB", "1TB"]),
            f("ram", "RAM", "select", ["2GB", "3GB", "4GB", "6GB", "8GB", "12GB", "16GB"]),
            f("sim", "SIM", "select", ["Single SIM", "Dual SIM", "eSIM", "Dual SIM + eSIM"]),
            f("network", "Network", "select", ["3G", "4G LTE", "5G"]),
            f("battery_health", "Battery Health", "number", placeholder="85"),
        ],
    },
    {
        "match": ["car", "vehicle", "motorcycle", "bike", "truck", "bus"],
        "filters": [
            f("make", "Make", "select", ["Toyota", "Mercedes-Benz", "BMW", "Audi", "Volkswagen", "Nissan", "Subaru", "Honda", "Mazda", "Mitsubishi", "Ford", "Isuzu", "Suzuki", "Bajaj", "TVS", "Yamaha", "Other"]),
            f("model", "Model", "text", placeholder="Harrier, Premio, Forester..."),
            f("year", "Year", "number", placeholder="2015"),
            f("mileage", "Mileage", "number", placeholder="85000"),
            f("fuel", "Fuel Type", "select", ["Petrol", "Diesel", "Hybrid", "Electric"]),
            f("transmission", "Transmission", "select", ["Automatic", "Manual", "Semi-automatic"]),
            f("engine_size", "Engine Size", "select", ["660cc", "1000cc", "1300cc", "1500cc", "1800cc", "2000cc", "2500cc", "3000cc", "3500cc+", "Other"]),
            f("body_type", "Body Type", "select", ["Sedan", "SUV", "Hatchback", "Wagon", "Pickup", "Van", "Truck", "Motorcycle"]),
            f("drive", "Drive", "select", ["2WD", "4WD", "AWD"]),
        ],
    },
    {
        "match": ["property", "house", "apartment", "land", "real estate", "rent", "sale"],
        "filters": [
            f("property_type", "Property Type", "select", ["House", "Apartment", "Studio", "Single Room", "Double Room", "Shop", "Office", "Warehouse", "Land", "Farm"]),
            f("purpose", "Purpose", "select", ["For Rent", "For Sale", "Short Stay"]),
            f("bedrooms", "Bedrooms", "select", ["1", "2", "3", "4", "5", "6+"]),
            f("bathrooms", "Bathrooms", "select", ["1", "2", "3", "4", "5+"]),
            f("furnished", "Furnished", "select", ["Furnished", "Semi-furnished", "Unfurnished"]),
            f("parking", "Parking", "select", ["Yes", "No"]),
            f("land_size", "Land Size", "text", placeholder="50x100, 12 decimals..."),
            f("title_status", "Title Status", "select", ["Private Mailo", "Freehold", "Leasehold", "Customary", "Agreement", "No Title"]),
        ],
    },
    {
        "match": ["job", "career", "vacancy"],
        "filters": [
            f("job_type", "Job Type", "select", ["Full-time", "Part-time", "Contract", "Internship", "Temporary", "Remote"]),
            f("experience_level", "Experience Level", "select", ["Entry Level", "1-2 years", "3-5 years", "5+ years"]),
            f("education_level", "Education Level", "select", ["UCE", "UACE", "Certificate", "Diploma", "Bachelor's Degree", "Master's Degree"]),
            f("salary_type", "Salary Type", "select", ["Monthly", "Weekly", "Daily", "Commission", "Negotiable"]),
            f("company", "Company", "text", placeholder="Company name"),
        ],
    },
    {
        "match": ["fashion", "clothing", "shoes", "bags", "watch", "jewelry", "jewellery"],
        "filters": [
            f("gender", "Gender", "select", ["Men", "Women", "Unisex", "Kids"]),
            f("size", "Size", "select", ["XS", "S", "M", "L", "XL", "XXL", "XXXL", "EU 36", "EU 37", "EU 38", "EU 39", "EU 40", "EU 41", "EU 42", "EU 43", "EU 44", "EU 45"]),
            f("color", "Color", "select", ["Black", "White", "Blue", "Red", "Green", "Yellow", "Brown", "Grey", "Pink", "Purple", "Other"]),
            f("material", "Material", "select", ["Cotton", "Leather", "Synthetic", "Denim", "Silk", "Wool", "Gold", "Silver", "Stainless Steel", "Other"]),
            f("brand", "Brand", "text", placeholder="Nike, Gucci, Rolex..."),
        ],
    },
    {
        "match": ["home", "kitchen", "furniture", "appliance"],
        "filters": [
            f("brand", "Brand", "select", ["Samsung", "LG", "Hisense", "Sony", "TCL", "Nasco", "Philips", "Kenwood", "Ramtons", "Other"]),
            f("type", "Type", "text", placeholder="Fridge, blender, sofa..."),
            f("material", "Material", "select", ["Wood", "Metal", "Plastic", "Glass", "Leather", "Fabric", "Other"]),
            f("color", "Color", "select", ["Black", "White", "Silver", "Brown", "Grey", "Red", "Blue", "Other"]),
            f("capacity", "Capacity", "text", placeholder="200L, 7kg, 1.5L..."),
        ],
    },
    {
        "match": ["health", "beauty", "cosmetic", "skincare", "hair"],
        "filters": [
            f("brand", "Brand", "text", placeholder="Brand name"),
            f("type", "Type", "select", ["Skincare", "Haircare", "Makeup", "Fragrance", "Salon Equipment", "Medical Equipment", "Other"]),
            f("gender", "Gender", "select", ["Men", "Women", "Unisex"]),
            f("expiry_date", "Expiry Date", "text", placeholder="MM/YYYY"),
        ],
    },
    {
        "match": ["baby", "babies", "mom", "kids", "children"],
        "filters": [
            f("age_range", "Age Range", "select", ["Newborn", "0-6 months", "6-12 months", "1-2 years", "3-5 years", "6-10 years", "10+ years"]),
            f("gender", "Gender", "select", ["Boy", "Girl", "Unisex"]),
            f("brand", "Brand", "text", placeholder="Brand name"),
            f("type", "Type", "text", placeholder="Stroller, clothes, toys..."),
        ],
    },
    {
        "match": ["sport", "outdoor", "fitness", "gym"],
        "filters": [
            f("sport_type", "Sport Type", "select", ["Football", "Basketball", "Tennis", "Golf", "Gym", "Cycling", "Camping", "Fishing", "Swimming", "Other"]),
            f("brand", "Brand", "text", placeholder="Nike, Adidas..."),
            f("size", "Size", "text", placeholder="Size"),
        ],
    },
    {
        "match": ["book", "office", "stationery"],
        "filters": [
            f("type", "Type", "select", ["Book", "Textbook", "Novel", "Printer", "Stationery", "Office Furniture", "Other"]),
            f("subject", "Subject", "text", placeholder="Math, Law, Business..."),
            f("author", "Author", "text", placeholder="Author name"),
            f("level", "Level", "select", ["Primary", "Secondary", "University", "Professional", "General"]),
        ],
    },
    {
        "match": ["service", "repair", "professional"],
        "filters": [
            f("service_type", "Service Type", "text", placeholder="Cleaning, repair, design..."),
            f("availability", "Availability", "select", ["Weekdays", "Weekends", "24/7", "By appointment"]),
            f("experience", "Experience", "select", ["Less than 1 year", "1-2 years", "3-5 years", "5+ years"]),
        ],
    },
    {
        "match": ["agriculture", "farm", "animal", "livestock", "pet"],
        "filters": [
            f("type", "Type", "text", placeholder="Cows, goats, seeds, feeds..."),
            f("breed", "Breed", "text", placeholder="Breed"),
            f("age", "Age", "text", placeholder="Age"),
            f("quantity", "Quantity", "number", placeholder="10"),
        ],
    },
]


class Command(BaseCommand):
    help = "Seed QOT category-specific filters for categories and subcategories."

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

        created_count = 0
        updated_count = 0

        for category in categories:
            category_text = norm(
                " ".join(
                    [
                        get_category_path(category),
                        get_category_label(category),
                        get_category_slug(category),
                    ]
                )
            )

            specs_by_key = {}

            for spec in COMMON:
                specs_by_key[spec["key"]] = spec

            matched_any = False

            for group in FILTER_GROUPS:
                if any(norm(keyword) in category_text for keyword in group["match"]):
                    matched_any = True

                    for spec in group["filters"]:
                        specs_by_key[spec["key"]] = spec

            if not matched_any:
                specs_by_key["type"] = f(
                    "type",
                    "Type",
                    "text",
                    placeholder="Type or style",
                )

            specs = list(specs_by_key.values())

            for index, spec in enumerate(specs, start=1):
                _, created = create_or_update_filter(
                    FilterModel,
                    category,
                    spec,
                    index,
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"{get_category_path(category)}: seeded {len(specs)} filters"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created {created_count}, updated {updated_count} category filters."
            )
        )