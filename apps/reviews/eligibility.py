from apps.chats.models import ChatMessage
from apps.listings.models import Listing


def accepted_offer_queryset(reviewer, listing=None):
    queryset = (
        ChatMessage.objects
        .filter(
            sender=reviewer,
            thread__buyer=reviewer,
            message_type=ChatMessage.TYPE_OFFER,
            offer_status=ChatMessage.OFFER_ACCEPTED,
        )
        .select_related(
            "thread",
            "thread__listing",
            "thread__listing__seller",
        )
        .order_by("-created_at", "-id")
    )

    if listing is not None:
        queryset = queryset.filter(thread__listing=listing)

    return queryset


def get_reviewable_offer(reviewer, listing):
    if listing.status != Listing.STATUS_SOLD or not listing.sold_at:
        return None

    return accepted_offer_queryset(reviewer, listing).first()
