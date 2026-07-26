from decimal import Decimal


FIELD_LABELS = {
    "title": "Title",
    "description": "Description",
    "price": "Price",
    "currency": "Currency",
    "condition": "Condition",
    "is_negotiable": "Price terms",
    "category": "Category",
    "city": "Location",
}


def _string_value(value):
    if isinstance(value, Decimal):
        return format(value, "f")
    if value is None:
        return ""
    return str(value)


def _attribute_display_value(attribute):
    if attribute.value_boolean is not None:
        return "Yes" if attribute.value_boolean else "No"

    if attribute.value_number is not None:
        return _string_value(attribute.value_number)

    raw_value = _string_value(attribute.value_text).strip()
    if not raw_value:
        return ""

    for option in attribute.category_filter.options.all():
        if str(option.value) == raw_value or str(option.id) == raw_value:
            return option.label

    return raw_value


def build_listing_review_snapshot(listing):
    attributes = {}
    for attribute in listing.attributes.select_related("category_filter").prefetch_related(
        "category_filter__options"
    ):
        key = str(attribute.category_filter_id)
        attributes[key] = {
            "label": attribute.category_filter.name,
            "value": _attribute_display_value(attribute),
        }

    images = []
    for image in listing.images.all().order_by("sort_order", "id"):
        images.append(
            {
                "id": image.id,
                "source": getattr(image.source_image, "name", "") or "",
                "detail": getattr(image.image, "name", "") or "",
                "card": getattr(image.card_image, "name", "") or "",
                "social": getattr(image.social_image, "name", "") or "",
                "sort_order": image.sort_order,
                "is_primary": image.is_primary,
            }
        )

    category_name = listing.category.name
    if getattr(listing.category, "parent", None):
        category_name = f"{listing.category.parent.name} / {category_name}"

    city_name = listing.city.name
    if getattr(listing.city, "region", None):
        city_name = f"{city_name}, {listing.city.region.name}"

    return {
        "title": listing.title,
        "description": listing.description,
        "price": _string_value(listing.price),
        "currency": listing.currency,
        "condition": listing.get_condition_display(),
        "is_negotiable": "Negotiable" if listing.is_negotiable else "Fixed price",
        "category": category_name,
        "city": city_name,
        "attributes": attributes,
        "images": images,
    }


def diff_listing_review_snapshots(before, after):
    if not before:
        return []

    changes = []
    for field, label in FIELD_LABELS.items():
        old_value = before.get(field, "")
        new_value = after.get(field, "")
        if old_value != new_value:
            changes.append(
                {
                    "field": field,
                    "label": label,
                    "before": old_value,
                    "after": new_value,
                    "kind": "field",
                }
            )

    old_attributes = before.get("attributes", {}) or {}
    new_attributes = after.get("attributes", {}) or {}
    for key in sorted(set(old_attributes) | set(new_attributes)):
        old_item = old_attributes.get(key, {}) or {}
        new_item = new_attributes.get(key, {}) or {}
        old_value = old_item.get("value", "")
        new_value = new_item.get("value", "")
        if old_value != new_value:
            changes.append(
                {
                    "field": f"attribute_{key}",
                    "label": new_item.get("label") or old_item.get("label") or "Specification",
                    "before": old_value or "Not provided",
                    "after": new_value or "Removed",
                    "kind": "attribute",
                }
            )

    old_images = before.get("images", []) or []
    new_images = after.get("images", []) or []
    old_by_id = {str(item.get("id")): item for item in old_images}
    new_by_id = {str(item.get("id")): item for item in new_images}
    added = [key for key in new_by_id if key not in old_by_id]
    removed = [key for key in old_by_id if key not in new_by_id]
    crop_changed = [
        key
        for key in set(old_by_id) & set(new_by_id)
        if (
            old_by_id[key].get("card") != new_by_id[key].get("card")
            or old_by_id[key].get("social") != new_by_id[key].get("social")
        )
    ]
    old_order = [str(item.get("id")) for item in old_images]
    new_order = [str(item.get("id")) for item in new_images]
    old_primary = next(
        (str(item.get("id")) for item in old_images if item.get("is_primary")),
        "",
    )
    new_primary = next(
        (str(item.get("id")) for item in new_images if item.get("is_primary")),
        "",
    )

    photo_notes = []
    if added:
        photo_notes.append(f"{len(added)} added")
    if removed:
        photo_notes.append(f"{len(removed)} removed")
    if crop_changed:
        photo_notes.append(f"{len(crop_changed)} display crop changed")
    if old_order != new_order:
        photo_notes.append("order changed")
    if old_primary != new_primary:
        photo_notes.append("cover photo changed")

    if photo_notes:
        changes.append(
            {
                "field": "photos",
                "label": "Photos",
                "before": f"{len(old_images)} photo{'s' if len(old_images) != 1 else ''}",
                "after": f"{len(new_images)} photo{'s' if len(new_images) != 1 else ''}",
                "summary": ", ".join(photo_notes),
                "kind": "photos",
            }
        )

    return changes
