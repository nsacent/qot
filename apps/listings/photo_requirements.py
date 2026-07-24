from dataclasses import dataclass

from rest_framework import serializers


@dataclass(frozen=True)
class CategoryPhotoRequirements:
    minimum: int
    maximum: int


DEFAULT_REQUIREMENTS = CategoryPhotoRequirements(minimum=1, maximum=8)

LARGE_VEHICLE_SLUGS = {
    "cars",
    "trucks",
    "buses",
    "boats",
    "heavy-equipment",
}

PROPERTY_BUILDING_SLUGS = {
    "houses",
    "houses-for-rent",
    "houses-for-sale",
    "apartments-for-rent",
    "commercial-property",
    "shops-offices",
    "hostels-rentals",
}

PROPERTY_LAND_SLUGS = {
    "land",
    "land-for-sale",
    "agricultural-land",
}

DETAILED_PRODUCT_SLUGS = {
    "phones",
    "mobile-phones",
    "laptops",
    "laptops-computers",
    "desktop-computers",
    "tablets",
    "cameras",
    "tvs",
    "gaming-consoles",
    "printers-scanners",
    "smart-watches",
    "appliances",
    "furniture",
    "sofas",
    "beds-mattresses",
    "tables-chairs",
    "wardrobes",
    "baby-furniture",
    "gym-equipment",
    "fitness-equipment",
    "bicycles",
    "musical-instruments",
    "farm-animals",
    "poultry",
    "dogs",
    "cats",
    "birds",
}

VEHICLE_PART_SLUGS = {
    "vehicle-spare-parts",
    "car-parts",
    "motorcycle-parts",
    "tyres-wheels",
}


def get_category_photo_requirements(category):
    slug = str(getattr(category, "slug", "") or "").lower()
    parent = getattr(category, "parent", None)
    parent_slug = str(getattr(parent, "slug", "") or "").lower()

    if slug == "short-stay-rentals":
        return CategoryPhotoRequirements(minimum=5, maximum=10)

    if slug in LARGE_VEHICLE_SLUGS or slug in PROPERTY_BUILDING_SLUGS:
        return CategoryPhotoRequirements(minimum=4, maximum=10)

    if slug in {"motorcycles", "rentals"} or slug in PROPERTY_LAND_SLUGS:
        return CategoryPhotoRequirements(minimum=3, maximum=10)

    if slug in DETAILED_PRODUCT_SLUGS or slug in VEHICLE_PART_SLUGS:
        return CategoryPhotoRequirements(minimum=2, maximum=8)

    if parent_slug in {"jobs", "services"} or slug in {
        "jobs",
        "services",
        "vehicle-services",
        "veterinary-services",
    }:
        return CategoryPhotoRequirements(minimum=1, maximum=5)

    return DEFAULT_REQUIREMENTS


def validate_category_photo_count(category, photo_count, field="images"):
    requirements = get_category_photo_requirements(category)
    category_name = getattr(category, "name", "This category")

    if photo_count < requirements.minimum:
        noun = "photo" if requirements.minimum == 1 else "photos"
        raise serializers.ValidationError({
            field: [
                f"{category_name} requires at least {requirements.minimum} {noun}."
            ]
        })

    if photo_count > requirements.maximum:
        raise serializers.ValidationError({
            field: [
                f"{category_name} allows a maximum of {requirements.maximum} photos."
            ]
        })

    return requirements
