from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.db.models import Q
import requests

from apps.common.emailing import build_branded_email_html

from .models import Notification, PushDevice


EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def _frontend_url(path):
    return f"{settings.FRONTEND_URL.rstrip('/')}{path}"


def _send_branded_email(
    *,
    subject,
    title,
    message,
    recipients,
    action_url="",
    action_label="Open QOT",
):
    recipients = sorted(
        {
            str(recipient).strip().lower()
            for recipient in recipients
            if str(recipient or "").strip()
        }
    )

    if not recipients:
        return 0

    plain_message = message

    if action_url:
        plain_message = f"{plain_message}\n\n{action_label}: {action_url}"

    plain_message = f"{plain_message}\n\nQOT Uganda\ninfo@qot.ug | 0200911678"
    html_message = build_branded_email_html(
        title=title,
        message=message,
        action_url=action_url,
        action_label=action_label,
    )

    email = EmailMultiAlternatives(
        subject=subject,
        body=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
    )
    email.attach_alternative(html_message, "text/html")
    return email.send(fail_silently=True)


def _notification_action(notification):
    if notification.notification_type == Notification.TYPE_LISTING_DELETED:
        return (
            _frontend_url("/account/notifications"),
            "View removal details",
        )

    if notification.chat_thread_id:
        return (
            _frontend_url(f"/account/messages/{notification.chat_thread_id}"),
            "Open conversation",
        )

    if notification.listing_id:
        return (_frontend_url(f"/ads/{notification.listing_id}"), "View ad")

    return (_frontend_url("/account/notifications"), "View notifications")


def _notification_app_url(notification):
    if notification.notification_type == Notification.TYPE_LISTING_DELETED:
        return "qot://notifications"

    if notification.chat_thread_id:
        return f"qot://messages/{notification.chat_thread_id}"

    if notification.listing_id:
        return f"qot://ads/{notification.listing_id}"

    return "qot://notifications"


def deliver_notification_push(notification_id):
    try:
        notification = Notification.objects.get(pk=notification_id)
    except Notification.DoesNotExist:
        return 0

    devices = list(
        PushDevice.objects.filter(
            user=notification.user,
            is_active=True,
        ).only("id", "expo_push_token")
    )
    if not devices:
        return 0

    delivered = 0
    app_url = _notification_app_url(notification)
    unread_count = Notification.objects.filter(
        user=notification.user,
        is_read=False,
    ).count()

    for offset in range(0, len(devices), 100):
        device_batch = devices[offset:offset + 100]
        messages = [
            {
                "to": device.expo_push_token,
                "title": notification.title,
                "body": notification.message,
                "sound": "default",
                "priority": "high",
                "channelId": "qot-updates",
                "badge": unread_count,
                "data": {
                    "url": app_url,
                    "notification_id": notification.id,
                    "notification_type": notification.notification_type,
                },
            }
            for device in device_batch
        ]

        try:
            response = requests.post(
                EXPO_PUSH_URL,
                json=messages,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=8,
            )
            response.raise_for_status()
            tickets = response.json().get("data", [])
        except (requests.RequestException, ValueError, AttributeError):
            continue

        invalid_device_ids = []
        for device, ticket in zip(device_batch, tickets):
            if ticket.get("status") == "ok":
                delivered += 1
                continue
            if ticket.get("details", {}).get("error") == "DeviceNotRegistered":
                invalid_device_ids.append(device.id)

        if invalid_device_ids:
            PushDevice.objects.filter(id__in=invalid_device_ids).update(is_active=False)

    return delivered


def deliver_notification_email(notification_id):
    try:
        notification = Notification.objects.select_related("user").get(
            pk=notification_id
        )
    except Notification.DoesNotExist:
        return 0

    if not notification.user.email:
        return 0

    action_url, action_label = _notification_action(notification)
    return _send_branded_email(
        subject=f"QOT Uganda: {notification.title}",
        title=notification.title,
        message=notification.message,
        recipients=[notification.user.email],
        action_url=action_url,
        action_label=action_label,
    )


def _admin_recipients():
    from apps.accounts.models import User

    configured = getattr(settings, "ADMIN_NOTIFICATION_EMAILS", []) or []
    database_recipients = (
        User.objects
        .filter(is_active=True, email__isnull=False)
        .filter(
            Q(role__in=[User.ROLE_ADMIN, User.ROLE_MODERATOR])
            | Q(is_staff=True)
            | Q(is_superuser=True)
        )
        .values_list("email", flat=True)
    )

    return [*configured, *database_recipients]


def _queue_admin_email(*, subject, title, message, action_path, action_label):
    transaction.on_commit(
        lambda: _send_branded_email(
            subject=subject,
            title=title,
            message=message,
            recipients=_admin_recipients(),
            action_url=_frontend_url(action_path),
            action_label=action_label,
        )
    )


def notify_admins_new_signup(user):
    contact = user.email or user.phone or "No contact supplied"
    _queue_admin_email(
        subject="QOT Uganda: New user signup",
        title="A new member joined QOT",
        message=f"{user.full_name} created an account using {contact}.",
        action_path=f"/admin/users/{user.pk}",
        action_label="Review user",
    )


def notify_admins_new_listing(listing):
    _queue_admin_email(
        subject="QOT Uganda: New ad awaiting review",
        title="A new ad needs moderation",
        message=(
            f"{listing.seller.full_name} submitted '{listing.title}' "
            "for approval."
        ),
        action_path=f"/admin/ads/{listing.pk}",
        action_label="Review ad",
    )


def notify_admins_new_report(report):
    _queue_admin_email(
        subject="QOT Uganda: New safety report",
        title="An ad was reported",
        message=(
            f"{report.reporter.full_name} reported '{report.listing.title}' "
            f"for {report.get_reason_display().lower()}."
        ),
        action_path=f"/admin/reports?listing={report.listing_id}",
        action_label="Review report",
    )


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
    preference_key=None,
):
    if preference_key:
        profile = getattr(user, "profile", None)
        preferences = getattr(profile, "notification_preferences", {}) or {}

        if preferences.get(preference_key, True) is False:
            return None

    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        listing=listing,
        chat_thread=chat_thread,
    )

    broadcast_notification(notification)
    transaction.on_commit(
        lambda notification_id=notification.pk: deliver_notification_email(
            notification_id
        )
    )
    transaction.on_commit(
        lambda notification_id=notification.pk: deliver_notification_push(
            notification_id
        )
    )

    return notification


def create_message_notification(thread, message):
    sender = message.sender

    if sender == thread.buyer:
        recipient = thread.seller
    else:
        recipient = thread.buyer

    if getattr(message, "message_type", "") == "offer" and message.offer_amount is not None:
        title = "New price offer"
        notification_message = (
            f"{sender.full_name} offered UGX {message.offer_amount:,.0f} "
            f"for '{thread.listing.title}'."
        )
    elif getattr(message, "message_type", "") == "callback":
        title = "Callback requested"
        notification_message = (
            f"{message.callback_name} requested a call about '{thread.listing.title}'."
        )
    else:
        title = "New message"
        notification_message = f"{sender.full_name} sent you a message."

    return create_notification(
        user=recipient,
        notification_type=Notification.TYPE_MESSAGE,
        title=title,
        message=notification_message,
        listing=thread.listing,
        chat_thread=thread,
        preference_key="messages",
    )


def create_offer_status_notification(thread, offer):
    status_label = {
        "accepted": "accepted",
        "declined": "declined",
        "withdrawn": "withdrawn",
    }.get(offer.offer_status)

    if not status_label:
        return None

    if offer.offer_status == "withdrawn":
        recipient = thread.seller
        title = "Offer withdrawn"
        message = (
            f"{thread.buyer.full_name} withdrew their UGX {offer.offer_amount:,.0f} "
            f"offer for '{thread.listing.title}'."
        )
    else:
        recipient = thread.buyer
        title = f"Offer {status_label}"
        message = (
            f"{thread.seller.full_name} {status_label} your UGX {offer.offer_amount:,.0f} "
            f"offer for '{thread.listing.title}'."
        )

    return create_notification(
        user=recipient,
        notification_type=Notification.TYPE_MESSAGE,
        title=title,
        message=message,
        listing=thread.listing,
        chat_thread=thread,
        preference_key="messages",
    )


def create_listing_approved_notification(listing):
    return create_notification(
        user=listing.seller,
        notification_type=Notification.TYPE_LISTING_APPROVED,
        title="Ad approved",
        message=f"Your ad '{listing.title}' has been approved and is now live.",
        listing=listing,
        preference_key="listing_approvals",
    )


def create_listing_rejected_notification(listing):
    reason = listing.rejection_reason or "Please review your listing details."

    return create_notification(
        user=listing.seller,
        notification_type=Notification.TYPE_LISTING_REJECTED,
        title="Ad rejected",
        message=f"Your ad '{listing.title}' was rejected. Reason: {reason}",
        listing=listing,
        preference_key="listing_rejections",
    )


def create_listing_deleted_notification(listing, reason):
    clean_reason = " ".join(str(reason or "").split())

    return create_notification(
        user=listing.seller,
        notification_type=Notification.TYPE_LISTING_DELETED,
        title="Your ad was removed by QOT",
        message=(
            f"Your ad '{listing.title}' was removed by QOT. "
            f"Reason: {clean_reason}"
        ),
        listing=listing,
    )


def create_listing_expired_notification(listing):
    return create_notification(
        user=listing.seller,
        notification_type=Notification.TYPE_LISTING_EXPIRED,
        title="Ad expired",
        message=(
            f"Your ad '{listing.title}' has expired. "
            "You can renew it to make it active again."
        ),
        listing=listing,
        preference_key="renewals",
    )


def create_favorite_notification(favorite):
    listing = favorite.listing

    if favorite.user_id == listing.seller_id:
        return None

    return create_notification(
        user=listing.seller,
        notification_type=Notification.TYPE_FAVORITE,
        title="Someone saved your ad",
        message=(
            f"{favorite.user.full_name} saved '{listing.title}' "
            "to their favourites."
        ),
        listing=listing,
        preference_key="favorites",
    )


def create_follow_notification(follow):
    return create_notification(
        user=follow.following,
        notification_type=Notification.TYPE_FOLLOW,
        title="You have a new follower",
        message=f"{follow.follower.full_name} started following your QOT profile.",
        preference_key="followers",
    )


def create_payment_paid_notification(payment):
    return create_notification(
        user=payment.user,
        notification_type=Notification.TYPE_SYSTEM,
        title="Payment confirmed",
        message=(
            f"Your payment {payment.reference} of "
            f"{payment.amount} {payment.currency} has been confirmed."
        ),
        listing=payment.listing,
    )


def create_payment_failed_notification(payment):
    return create_notification(
        user=payment.user,
        notification_type=Notification.TYPE_SYSTEM,
        title="Payment failed",
        message=(
            f"Your payment {payment.reference} was not successful. "
            "Please try again or contact support."
        ),
        listing=payment.listing,
    )


def create_saved_search_match_notification(user, listing, saved_search):
    return create_notification(
        user=user,
        notification_type=Notification.TYPE_SYSTEM,
        title="New ad matches your saved search",
        message=(
            f"A new ad '{listing.title}' matches your saved search "
            f"'{saved_search.name}'."
        ),
        listing=listing,
    )
