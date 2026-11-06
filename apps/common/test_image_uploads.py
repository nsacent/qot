from io import BytesIO
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image
from rest_framework.exceptions import ValidationError

from .image_uploads import normalize_heif_upload


FIXTURES = Path(__file__).parent / "test_fixtures" / "heif"


class HeifUploadNormalizationTests(SimpleTestCase):
    def test_real_spatial_photo_and_mislabeled_uploads_become_jpeg(self):
        contents = (FIXTURES / "spatial_photo.heic").read_bytes()
        for name, content_type in (
            ("iphone.HEIC", "image/heic"),
            ("iphone.heif", "image/heif"),
            ("iphone.hif", "application/octet-stream"),
            ("iphone.jpg", "image/jpeg"),
        ):
            with self.subTest(name=name):
                original = SimpleUploadedFile(name, contents, content_type=content_type)
                converted = normalize_heif_upload(original, max_bytes=5 * 1024 * 1024)
                self.assertEqual(converted.name, "iphone.jpg")
                self.assertEqual(converted.content_type, "image/jpeg")
                self.assertEqual(original.tell(), 0)
                with Image.open(converted) as image:
                    image.load()
                    self.assertEqual(image.format, "JPEG")
                    self.assertEqual(image.size, (2560, 2560))
                    self.assertFalse(image.getexif())

    def test_unsupported_depth_item_does_not_block_primary_image(self):
        upload = SimpleUploadedFile(
            "depth.heic", (FIXTURES / "unsupported_depth_image.heic").read_bytes(),
            content_type="image/heic",
        )
        converted = normalize_heif_upload(upload, max_bytes=5 * 1024 * 1024)
        with Image.open(converted) as image:
            self.assertEqual(image.size, (128, 128))

    def test_ordinary_images_and_documents_are_preserved(self):
        output = BytesIO()
        Image.new("RGB", (20, 30)).save(output, format="PNG")
        for name, data, content_type in (
            ("photo.png", output.getvalue(), "image/png"),
            ("file.pdf", b"%PDF-1.4 example", "application/pdf"),
        ):
            upload = SimpleUploadedFile(name, data, content_type=content_type)
            self.assertIs(normalize_heif_upload(upload, max_bytes=5 * 1024 * 1024), upload)
            self.assertEqual(upload.read(), data)

    def test_corrupt_heif_is_rejected(self):
        upload = SimpleUploadedFile("broken.heic", b"not a photo", content_type="image/heic")
        with self.assertRaises(ValidationError):
            normalize_heif_upload(upload, max_bytes=5 * 1024 * 1024)

    def test_avif_is_not_normalized_into_an_allowed_profile_or_attachment_type(self):
        output = BytesIO()
        Image.new("RGB", (20, 30)).save(output, format="AVIF")
        for name, content_type in (("photo.avif", "image/avif"), ("photo.heic", "image/heic")):
            with self.subTest(name=name):
                upload = SimpleUploadedFile(name, output.getvalue(), content_type=content_type)
                self.assertIs(normalize_heif_upload(upload, max_bytes=5 * 1024 * 1024), upload)
                self.assertEqual(upload.read(), output.getvalue())

    def test_original_size_limit_is_checked_before_conversion(self):
        upload = SimpleUploadedFile(
            "large.heic", (FIXTURES / "spatial_photo.heic").read_bytes(),
            content_type="image/heic",
        )
        with self.assertRaises(ValidationError):
            normalize_heif_upload(upload, max_bytes=1024 * 1024)
