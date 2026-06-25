from decimal import Decimal, InvalidOperation

from apps.notifications.services import create_saved_search_match_notification
from apps.searches.models import SavedSearch, SavedSearchAlertLog


def get_filter_value(filters, key):
    if not filters:
        return None

    return filters.get(key)


def listing_matches_saved_search(listing, saved_search):
    query = (saved_search.query or "").strip().lower()
    filters = saved_search.filters or {}

    if query:
        searchable_text = " ".join(
            [
                listing.title or "",
                listing.description or "",
                listing.category.name if listing.category else "",
                listing.city.name if listing.city else "",
            ]
        ).lower()

        if query not in searchable_text:
            return False

    category = get_filter_value(filters, "category")
    city = get_filter_value(filters, "city")
    min_price = get_filter_value(filters, "min_price")
    max_price = get_filter_value(filters, "max_price")

    if category and listing.category:
        category_text = str(category)

        category_matches = (
            str(listing.category_id) == category_text
            or listing.category.slug == category_text
        )

        parent_matches = False

        if listing.category.parent:
            parent_matches = (
                str(listing.category.parent_id) == category_text
                or listing.category.parent.slug == category_text
            )

        if not category_matches and not parent_matches:
            return False

    if city and listing.city:
        city_text = str(city)

        if str(listing.city_id) != city_text and listing.city.slug != city_text:
            return False

    if min_price is not None:
        try:
            if listing.price < Decimal(str(min_price)):
                return False
        except (InvalidOperation, ValueError):
            pass

    if max_price is not None:
        try:
            if listing.price > Decimal(str(max_price)):
                return False
        except (InvalidOperation, ValueError):
            pass

    return True


def notify_saved_search_matches_for_listing(listing):
    if listing.status != listing.STATUS_ACTIVE:
        return 0

    saved_searches = (
        SavedSearch.objects
        .select_related("user")
        .filter(
            user__is_active=True,
            user__is_banned=False,
            notify_user=True,
        )
    )

    sent_count = 0

    for saved_search in saved_searches:
        if saved_search.user_id == listing.seller_id:
            continue

        already_sent = SavedSearchAlertLog.objects.filter(
            saved_search=saved_search,
            user=saved_search.user,
            listing=listing,
        ).exists()

        if already_sent:
            continue

        if listing_matches_saved_search(listing, saved_search):
            create_saved_search_match_notification(
                user=saved_search.user,
                listing=listing,
                saved_search=saved_search,
            )

            SavedSearchAlertLog.objects.create(
                saved_search=saved_search,
                user=saved_search.user,
                listing=listing,
            )

            sent_count += 1

    return sent_count