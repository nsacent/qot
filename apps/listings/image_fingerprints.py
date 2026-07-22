import hashlib

from rest_framework.exceptions import ValidationError

from .models import Listing, ListingImage, PendingListingImage


DUPLICATE_AD_IMAGE_MESSAGE = (
    "This photo is already used in another one of your ads. "
    "Choose a different photo."
)
DUPLICATE_SELECTION_MESSAGE = "You selected the same photo more than once."
DUPLICATE_DRAFT_IMAGE_MESSAGE = (
    "This photo has already been selected for your current ad draft."
)


def calculate_content_hash(image_file):
    """Return a SHA-256 digest without leaving the file pointer consumed."""
    original_position = None

    try:
        original_position = image_file.tell()
    except (AttributeError, OSError, ValueError):
        pass

    try:
        image_file.seek(0)
    except (AttributeError, OSError, ValueError):
        image_file.open("rb")

    digest = hashlib.sha256()

    if hasattr(image_file, "chunks"):
        for chunk in image_file.chunks():
            digest.update(chunk)
    else:
        while True:
            chunk = image_file.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)

    try:
        image_file.seek(original_position or 0)
    except (AttributeError, OSError, ValueError):
        pass

    return digest.hexdigest()


def ensure_image_hash(image_record):
    if image_record.content_hash:
        return image_record.content_hash

    if not image_record.image:
        return ""

    try:
        content_hash = calculate_content_hash(image_record.image)
    except (OSError, ValueError):
        return ""

    type(image_record).objects.filter(
        pk=image_record.pk,
        content_hash="",
    ).update(content_hash=content_hash)
    image_record.content_hash = content_hash
    return content_hash


def _backfill_missing_hashes(queryset):
    for image_record in queryset.filter(content_hash="").iterator():
        ensure_image_hash(image_record)


def find_duplicate_listing_image(user, content_hash, exclude_listing_id=None):
    queryset = ListingImage.objects.filter(
        listing__seller=user,
    ).exclude(
        listing__status=Listing.STATUS_DELETED,
    )

    if exclude_listing_id is not None:
        queryset = queryset.exclude(listing_id=exclude_listing_id)

    _backfill_missing_hashes(queryset)

    return (
        queryset.filter(content_hash=content_hash)
        .select_related("listing")
        .first()
    )


def find_duplicate_pending_image(user, content_hash, exclude_pending_ids=None):
    queryset = PendingListingImage.objects.filter(user=user)

    if exclude_pending_ids:
        queryset = queryset.exclude(pk__in=exclude_pending_ids)

    _backfill_missing_hashes(queryset)
    return queryset.filter(content_hash=content_hash).first()


def validate_image_for_user(
    *,
    user,
    image_file,
    exclude_listing_id=None,
    exclude_pending_ids=None,
    check_pending=False,
    seen_hashes=None,
    error_field="image",
):
    content_hash = calculate_content_hash(image_file)

    if seen_hashes is not None and content_hash in seen_hashes:
        raise ValidationError({error_field: [DUPLICATE_SELECTION_MESSAGE]})

    if find_duplicate_listing_image(
        user,
        content_hash,
        exclude_listing_id=exclude_listing_id,
    ):
        raise ValidationError({error_field: [DUPLICATE_AD_IMAGE_MESSAGE]})

    if check_pending and find_duplicate_pending_image(
        user,
        content_hash,
        exclude_pending_ids=exclude_pending_ids,
    ):
        raise ValidationError({error_field: [DUPLICATE_DRAFT_IMAGE_MESSAGE]})

    if seen_hashes is not None:
        seen_hashes.add(content_hash)

    return content_hash


def validate_staged_image_for_user(
    *,
    user,
    image_record,
    seen_hashes=None,
    error_field="images",
):
    content_hash = ensure_image_hash(image_record)

    if not content_hash:
        return ""

    if seen_hashes is not None and content_hash in seen_hashes:
        raise ValidationError({error_field: [DUPLICATE_SELECTION_MESSAGE]})

    if find_duplicate_listing_image(user, content_hash):
        raise ValidationError({error_field: [DUPLICATE_AD_IMAGE_MESSAGE]})

    if seen_hashes is not None:
        seen_hashes.add(content_hash)

    return content_hash
