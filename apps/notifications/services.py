from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Notification


def broadcast_notification(notification):
    channel_layer = get_channel_layer()

    if channel_layer is None:
        return

    group_name = f"user_notifications_{notification.user_id}"

    payload = {
        "id": notification.id,
        "notification_type": notification.notification_type,
        "title": notification.title,
        "message": notification.message,
        "listing": notification.listing_id,
        "chat_thread": notification.chat_thread_id,
        "is_read": notification.is_read,
        "created_at": notification.created_at.isoformat(),
    }

    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "notification_message",
            "notification": payload,
        },
    )


def create_notification(
    *,
    user,
    notification_type,
    title,
    message,
    listing=None,
    chat_thread=None,
):
    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        listing=listing,
        chat_thread=chat_thread,
    )

    broadcast_notification(notification)

    return notification


def create_message_notification(thread, message):
    sender = message.sender

    if sender == thread.buyer:
        recipient = thread.seller
    else:
        recipient = thread.buyer

    return create_notification(
        user=recipient,
        notification_type=Notification.TYPE_MESSAGE,
        title="New message",
        message=f"{sender.full_name} sent you a message.",
        listing=thread.listing,
        chat_thread=thread,
    )


def create_listing_approved_notification(listing):
    return create_notification(
        user=listing.seller,
        notification_type=Notification.TYPE_LISTING_APPROVED,
        title="Listing approved",
        message=f"Your listing '{listing.title}' has been approved and is now live.",
        listing=listing,
    )


def create_listing_rejected_notification(listing):
    reason = listing.rejection_reason or "Please review your listing details."

    return create_notification(
        user=listing.seller,
        notification_type=Notification.TYPE_LISTING_REJECTED,
        title="Listing rejected",
        message=f"Your listing '{listing.title}' was rejected. Reason: {reason}",
        listing=listing,
    )


def create_listing_expired_notification(listing):
    return create_notification(
        user=listing.seller,
        notification_type=Notification.TYPE_LISTING_EXPIRED,
        title="Listing expired",
        message=f"Your listing '{listing.title}' has expired. You can renew it to make it active again.",
        listing=listing,
    )