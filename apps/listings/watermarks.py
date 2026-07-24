from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageStat


WATERMARK_TEXT = "QOT"
WATERMARK_ALPHA = 68


def _watermark_font(size):
    candidates = (
        "DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
    )

    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue

    return ImageFont.load_default()


def apply_qot_watermark(image):
    """Return an RGBA image with a subtle, contrast-aware QOT wordmark."""
    watermarked_source = image.convert("RGBA")
    shortest_side = max(1, min(watermarked_source.size))
    font_size = max(18, int(shortest_side * 0.10))
    font = _watermark_font(font_size)
    overlay = Image.new("RGBA", watermarked_source.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    text_box = draw.textbbox((0, 0), WATERMARK_TEXT, font=font)
    text_width = text_box[2] - text_box[0]
    text_height = text_box[3] - text_box[1]
    left = max(0, (watermarked_source.width - text_width) // 2)
    top = max(0, (watermarked_source.height - text_height) // 2)
    sample_padding = max(6, font_size // 4)
    sample_box = (
        max(0, left - sample_padding),
        max(0, top - sample_padding),
        min(watermarked_source.width, left + text_width + sample_padding),
        min(watermarked_source.height, top + text_height + sample_padding),
    )
    local_brightness = ImageStat.Stat(
        watermarked_source.convert("L").crop(sample_box)
    ).mean[0]
    text_colour = 20 if local_brightness >= 145 else 255
    draw.text(
        (left, top - text_box[1]),
        WATERMARK_TEXT,
        font=font,
        fill=(text_colour, text_colour, text_colour, WATERMARK_ALPHA),
    )

    return Image.alpha_composite(watermarked_source, overlay)


def add_qot_watermark(image_file):
    """Return a watermarked image file without modifying the source upload."""
    try:
        image_file.seek(0)
    except (AttributeError, OSError, ValueError):
        image_file.open("rb")

    with Image.open(image_file) as source:
        source_format = (source.format or "PNG").upper()
        image = ImageOps.exif_transpose(source).convert("RGBA")

    watermarked = apply_qot_watermark(image)
    output = BytesIO()
    save_format = source_format if source_format in {"JPEG", "PNG", "WEBP"} else "PNG"
    save_options = {}

    if save_format == "JPEG":
        watermarked = watermarked.convert("RGB")
        save_options = {"quality": 90, "optimize": True}
    elif save_format == "WEBP":
        save_options = {"quality": 90, "method": 4}
    else:
        save_options = {"optimize": True}

    watermarked.save(output, format=save_format, **save_options)
    output.seek(0)

    original_name = Path(getattr(image_file, "name", "advert.png")).name
    return ContentFile(output.read(), name=original_name)
