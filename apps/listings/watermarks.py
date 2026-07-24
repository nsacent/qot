from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageOps


WATERMARK_ALPHA = 48
WATERMARK_COLOR = (249, 115, 22)
LOGO_VIEWBOX = (240, 100)


def _qot_logo_mask(width):
    """Render the same QOT geometry used by the website logo."""
    width = max(72, int(width))
    height = max(30, round(width * LOGO_VIEWBOX[1] / LOGO_VIEWBOX[0]))
    antialias = 4
    scale = width * antialias / LOGO_VIEWBOX[0]
    mask = Image.new("L", (width * antialias, height * antialias), 0)
    draw = ImageDraw.Draw(mask)

    def point(x, y):
        return round(x * scale), round(y * scale)

    stroke_width = max(1, round(18 * scale))
    for center_x in (40, 124):
        center_y = 42
        radius = 29
        draw.ellipse(
            (
                *point(center_x - radius, center_y - radius),
                *point(center_x + radius, center_y + radius),
            ),
            outline=255,
            width=stroke_width,
        )

    draw.polygon(
        [
            point(45.77, 60.5),
            point(58.5, 47.77),
            point(94.23, 83.5),
            point(81.5, 96.23),
        ],
        fill=255,
    )

    t_outline = [
        (178, 12), (196, 3), (196, 24), (226, 24), (226, 43),
        (196, 43), (196, 68), (197, 73), (200, 77), (204, 79),
        (208, 80), (224, 80), (224, 98), (208, 98), (201, 97),
        (195, 95), (190, 92), (186, 88), (182, 83), (180, 76),
        (178, 68),
    ]
    draw.polygon([point(x, y) for x, y in t_outline], fill=255)

    return mask.resize((width, height), Image.Resampling.LANCZOS)


def apply_qot_watermark(image):
    """Return an RGBA image with a faint, shadow-free QOT logo."""
    watermarked_source = image.convert("RGBA")
    shortest_side = max(1, min(watermarked_source.size))
    logo_width = min(
        int(watermarked_source.width * 0.34),
        int(shortest_side * 0.52),
    )
    logo_mask = _qot_logo_mask(logo_width)
    logo_alpha = logo_mask.point(
        lambda value: round(value * WATERMARK_ALPHA / 255)
    )
    logo = Image.new("RGBA", logo_mask.size, (*WATERMARK_COLOR, 0))
    logo.putalpha(logo_alpha)
    overlay = Image.new("RGBA", watermarked_source.size, (0, 0, 0, 0))
    left = max(0, (watermarked_source.width - logo.width) // 2)
    top = max(0, (watermarked_source.height - logo.height) // 2)
    overlay.alpha_composite(logo, (left, top))

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
