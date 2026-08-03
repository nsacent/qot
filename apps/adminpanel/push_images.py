from io import BytesIO
from pathlib import Path
from uuid import uuid4

from django.core.files.base import ContentFile
from PIL import Image, ImageOps


MAX_PUSH_IMAGE_BYTES = 900 * 1024
MAX_PUSH_IMAGE_SIZE = (1600, 1200)


def optimize_push_image(upload):
    """Return a broadly supported notification image below FCM's 1 MB limit."""
    upload.seek(0)
    with Image.open(upload) as source:
        image = ImageOps.exif_transpose(source)
        if image.mode in {"RGBA", "LA"} or (
            image.mode == "P" and "transparency" in image.info
        ):
            rgba = image.convert("RGBA")
            background = Image.new("RGB", rgba.size, "white")
            background.paste(rgba, mask=rgba.getchannel("A"))
            image = background
        else:
            image = image.convert("RGB")

        image.thumbnail(MAX_PUSH_IMAGE_SIZE, Image.Resampling.LANCZOS)

        encoded = BytesIO()
        for quality in (84, 76, 68, 60, 52):
            encoded.seek(0)
            encoded.truncate(0)
            image.save(
                encoded,
                format="JPEG",
                quality=quality,
                optimize=True,
                progressive=True,
            )
            if encoded.tell() <= MAX_PUSH_IMAGE_BYTES:
                break

    safe_stem = "".join(
        character
        for character in Path(upload.name or "notification").stem
        if character.isalnum() or character in {"-", "_"}
    )[:60] or "notification"
    return ContentFile(
        encoded.getvalue(),
        name=f"{safe_stem}-{uuid4().hex[:10]}.jpg",
    )
