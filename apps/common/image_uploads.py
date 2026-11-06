from io import BytesIO
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image, ImageOps
from pillow_heif import get_file_mimetype
from rest_framework import serializers


HEIF_EXTENSIONS = {".heic", ".heics", ".heif", ".heifs", ".hif"}
HEIF_CONTENT_TYPES = {
    "image/heic", "image/heic-sequence", "image/x-heic",
    "image/heif", "image/heif-sequence", "image/x-heif",
}


def normalize_heif_upload(upload, *, max_bytes):
    """Store iPhone photos as browser-readable JPEG, retaining ordinary uploads."""
    if upload is None:
        return upload

    name = getattr(upload, "name", "photo") or "photo"
    hinted_heif = (
        Path(name).suffix.lower() in HEIF_EXTENSIONS
        or str(getattr(upload, "content_type", "")).lower() in HEIF_CONTENT_TYPES
    )
    upload.seek(0)
    try:
        header = upload.read(12)
        heif_header = header[4:8] == b"ftyp" and get_file_mimetype(header) in HEIF_CONTENT_TYPES
    finally:
        upload.seek(0)

    if not hinted_heif and not heif_header:
        return upload

    if upload.size > max_bytes:
        raise serializers.ValidationError(
            f"Image must be {max_bytes // (1024 * 1024)}MB or smaller."
        )

    try:
        with Image.open(upload) as source:
            if source.format != "HEIF":
                return upload
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((2560, 2560), Image.Resampling.LANCZOS)
            output = BytesIO()
            image.save(output, format="JPEG", quality=88, optimize=True)
    except (OSError, ValueError, SyntaxError, EOFError, RuntimeError, Image.DecompressionBombError) as error:
        raise serializers.ValidationError(
            "This HEIC/HEIF photo could not be read. Try exporting it as JPEG."
        ) from error
    finally:
        upload.seek(0)

    contents = output.getvalue()
    if len(contents) > max_bytes:
        raise serializers.ValidationError(
            f"Converted image must be {max_bytes // (1024 * 1024)}MB or smaller."
        )

    stem = Path(name).stem or "photo"
    return SimpleUploadedFile(f"{stem}.jpg", contents, content_type="image/jpeg")
