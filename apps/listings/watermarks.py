from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont, ImageOps


WATERMARK_TEXT = "QOT"


def _watermark_font(size):
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size=size)
    except OSError:
        return ImageFont.load_default()


def apply_qot_watermark(image):
    """Return an RGBA image with a subtle, centred QOT watermark."""
    watermarked_source = image.convert("RGBA")
    shortest_side = max(1, min(watermarked_source.size))
    font_size = max(16, int(shortest_side * 0.11))
    font = _watermark_font(font_size)
    overlay = Image.new("RGBA", watermarked_source.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    text_box = draw.textbbox((0, 0), WATERMARK_TEXT, font=font, stroke_width=1)
    text_width = text_box[2] - text_box[0]
    text_height = text_box[3] - text_box[1]
    padding_x = max(8, int(font_size * 0.42))
    padding_y = max(5, int(font_size * 0.22))
    box_width = text_width + (padding_x * 2)
    box_height = text_height + (padding_y * 2)
    left = max(0, (watermarked_source.width - box_width) // 2)
    top = max(0, (watermarked_source.height - box_height) // 2)
    radius = max(6, int(box_height * 0.28))

    draw.rounded_rectangle(
        (left, top, left + box_width, top + box_height),
        radius=radius,
        fill=(15, 23, 42, 52),
        outline=(255, 255, 255, 38),
        width=max(1, int(shortest_side * 0.002)),
    )
    draw.text(
        (left + padding_x, top + padding_y - text_box[1]),
        WATERMARK_TEXT,
        font=font,
        fill=(255, 255, 255, 142),
        stroke_width=1,
        stroke_fill=(15, 23, 42, 72),
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
