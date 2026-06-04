from .models import Notification


def create_message_notification(thread, message):
    sender = message.sender

    if sender == thread.buyer:
        recipient = thread.seller
    else:
        recipient = thread.buyer

    return Notification.objects.create(
        user=recipient,
        notification_type=Notification.TYPE_MESSAGE,
        title="New message",
        message=f"{sender.full_name} sent you a message.",
        listing=thread.listing,
        chat_thread=thread,
    )

def create_listing_approved_notification(listing):
    return Notification.objects.create(
        user=listing.seller,
        notification_type=Notification.TYPE_LISTING_APPROVED,
        title="Listing approved",
        message=f"Your listing '{listing.title}' has been approved and is now live.",
        listing=listing,
    )


def create_listing_rejected_notification(listing):
    reason = listing.rejection_reason or "Please review your listing details."

    return Notification.objects.create(
        user=listing.seller,
        notification_type=Notification.TYPE_LISTING_REJECTED,
        title="Listing rejected",
        message=f"Your listing '{listing.title}' was rejected. Reason: {reason}",
        listing=listing,
    )


def create_listing_expired_notification(listing):
    return Notification.objects.create(
        user=listing.seller,
        notification_type=Notification.TYPE_LISTING_EXPIRED,
        title="Listing expired",
        message=f"Your listing '{listing.title}' has expired. You can renew it to make it active again.",
        listing=listing,
    )