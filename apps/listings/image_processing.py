from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from django.core.files.base import ContentFile
from PIL import Image, ImageOps

from .watermarks import apply_qot_watermark


SOURCE_MAX_EDGE = 2560
DETAIL_MAX_EDGE = 1920
CARD_SIZE = (800, 600)
SOCIAL_SIZE = (1200, 630)
MIN_IMAGE_SIZE = (600, 450)


@dataclass
class ProcessedListingImages:
    source: ContentFile
    detail: ContentFile
    card: ContentFile
    social: ContentFile


@dataclass
class ListingImageVariants:
    detail: ContentFile
    card: ContentFile
    social: ContentFile


def normalize_crop_value(value, default, minimum, maximum):
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default

    return min(max(number, minimum), maximum)


def normalize_crop(crop_x=0.5, crop_y=0.5, crop_zoom=1.0):
    return (
        normalize_crop_value(crop_x, 0.5, 0.0, 1.0),
        normalize_crop_value(crop_y, 0.5, 0.0, 1.0),
        normalize_crop_value(crop_zoom, 1.0, 1.0, 2.5),
    )


def _open_clean_image(image_file):
    try:
        image_file.seek(0)
    except (AttributeError, OSError, ValueError):
        image_file.open("rb")

    with Image.open(image_file) as source:
        image = ImageOps.exif_transpose(source)

        if image.mode not in {"RGB", "RGBA"}:
            image = image.convert("RGBA" if "transparency" in image.info else "RGB")
        else:
            image = image.copy()

    return image


def _resize_to_max_edge(image, max_edge):
    result = image.copy()

    if max(result.size) > max_edge:
        result.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)

    return result


def _crop_to_aspect(image, size, crop_x, crop_y, crop_zoom):
    target_width, target_height = size
    target_ratio = target_width / target_height
    image_width, image_height = image.size
    image_ratio = image_width / image_height

    if image_ratio > target_ratio:
        base_height = image_height
        base_width = base_height * target_ratio
    else:
        base_width = image_width
        base_height = base_width / target_ratio

    crop_width = max(1, base_width / crop_zoom)
    crop_height = max(1, base_height / crop_zoom)
    center_x = crop_x * image_width
    center_y = crop_y * image_height
    left = min(max(center_x - (crop_width / 2), 0), image_width - crop_width)
    top = min(max(center_y - (crop_height / 2), 0), image_height - crop_height)
    right = left + crop_width
    bottom = top + crop_height

    return image.crop((round(left), round(top), round(right), round(bottom))).resize(
        size,
        Image.Resampling.LANCZOS,
    )


def _save_webp(image, stem, suffix, quality):
    output = BytesIO()
    save_image = image.convert("RGBA") if image.mode == "RGBA" else image.convert("RGB")
    save_image.save(
        output,
        format="WEBP",
        quality=quality,
        method=5,
        optimize=True,
    )
    output.seek(0)
    return ContentFile(
        output.read(),
        name=f"{stem}-{suffix}-{uuid4().hex[:12]}.webp",
    )


def prepare_listing_source(image_file):
    source = _resize_to_max_edge(_open_clean_image(image_file), SOURCE_MAX_EDGE)
    original_stem = Path(getattr(image_file, "name", "qot-photo")).stem or "qot-photo"
    safe_stem = "".join(
        character
        for character in original_stem
        if character.isalnum() or character in "-_"
    )[:60] or "qot-photo"
    return _save_webp(source, safe_stem, "source", 90)


def generate_listing_variants(source_file, crop_x=0.5, crop_y=0.5, crop_zoom=1.0):
    crop_x, crop_y, crop_zoom = normalize_crop(crop_x, crop_y, crop_zoom)
    source = _open_clean_image(source_file)
    stem = Path(getattr(source_file, "name", "qot-photo")).stem or "qot-photo"
    detail = apply_qot_watermark(_resize_to_max_edge(source, DETAIL_MAX_EDGE))
    card = apply_qot_watermark(
        _crop_to_aspect(source, CARD_SIZE, crop_x, crop_y, crop_zoom)
    )
    social = apply_qot_watermark(
        _crop_to_aspect(source, SOCIAL_SIZE, crop_x, crop_y, crop_zoom)
    )

    return ListingImageVariants(
        detail=_save_webp(detail, stem, "detail", 84),
        card=_save_webp(card, stem, "card", 78),
        social=_save_webp(social, stem, "social", 82),
    )


def process_listing_upload(image_file, crop_x=0.5, crop_y=0.5, crop_zoom=1.0):
    source = prepare_listing_source(image_file)
    variants = generate_listing_variants(source, crop_x, crop_y, crop_zoom)
    return ProcessedListingImages(
        source=source,
        detail=variants.detail,
        card=variants.card,
        social=variants.social,
    )


def delete_listing_image_files(image_record, exclude_names=None):
    excluded = set(exclude_names or [])

    for field_name in ("image", "source_image", "card_image", "social_image"):
        field = getattr(image_record, field_name, None)
        name = getattr(field, "name", "")

        if not name or name in excluded:
            continue

        field.delete(save=False)
