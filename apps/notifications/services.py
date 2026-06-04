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