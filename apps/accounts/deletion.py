from django.db import transaction

from apps.adminpanel.models import AdminActivityLog
from apps.chats.models import ChatMessage, ChatMessageAttachment
from apps.listings.models import ListingImage, PendingListingImage


def _remember_file(files, field):
    name = str(getattr(field, "name", "") or "").strip()
    storage = getattr(field, "storage", None)
    if name and storage:
        files[(storage.__class__, name)] = (storage, name)


def _account_media_files(user):
    files = {}

    profile = getattr(user, "profile", None)
    if profile:
        _remember_file(files, profile.avatar)
        _remember_file(files, profile.cover_photo)

    listing_images = ListingImage.objects.filter(listing__seller=user).iterator()
    for image in listing_images:
        for field_name in ("image", "source_image", "card_image", "social_image"):
            _remember_file(files, getattr(image, field_name))

    for image in PendingListingImage.objects.filter(user=user).iterator():
        for field_name in ("image", "source_image", "card_image", "social_image"):
            _remember_file(files, getattr(image, field_name))

    for message in ChatMessage.objects.filter(sender=user).iterator():
        _remember_file(files, message.image)

    attachments = ChatMessageAttachment.objects.filter(message__sender=user).iterator()
    for attachment in attachments:
        _remember_file(files, attachment.file)

    return list(files.values())


def permanently_delete_user_account(user):
    """Delete the user and remove media they uploaded after the DB commit."""
    media_files = _account_media_files(user)

    with transaction.atomic():
        AdminActivityLog.objects.filter(actor=user).update(
            actor_name="Deleted QOT user",
            actor_email="",
        )
        user.delete()

        def delete_media():
            for storage, name in media_files:
                try:
                    storage.delete(name)
                except Exception:
                    # The database deletion must remain final even when external
                    # object storage is temporarily unavailable. Orphan cleanup
                    # can safely retry the file later.
                    continue

        transaction.on_commit(delete_media)
