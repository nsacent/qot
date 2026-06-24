from django.db.models import Avg

from apps.accounts.models import UserProfile
from apps.listings.models import Listing


def calculate_user_trust_score(user):
    score = 0

    # Verified account
    if user.is_verified:
        score += 30

    # Active account
    if user.is_active and not user.is_banned:
        score += 10

    # Listings activity
    active_listings_count = Listing.objects.filter(
        seller=user,
        status=Listing.STATUS_ACTIVE,
    ).count()

    if active_listings_count >= 1:
        score += 10

    if active_listings_count >= 5:
        score += 10

    if active_listings_count >= 10:
        score += 10

    # Reviews
    reviews = user.received_reviews.filter(is_visible=True)

    total_reviews = reviews.count()

    if total_reviews > 0:
        average_rating = reviews.aggregate(
            average=Avg("rating"),
        )["average"] or 0

        if average_rating >= 4.5:
            score += 30
        elif average_rating >= 4.0:
            score += 25
        elif average_rating >= 3.5:
            score += 15
        elif average_rating >= 3.0:
            score += 10
        else:
            score += 5

    if total_reviews >= 5:
        score += 10

    if total_reviews >= 20:
        score += 10

    # Penalties
    rejected_listings_count = Listing.objects.filter(
        seller=user,
        status=Listing.STATUS_REJECTED,
    ).count()

    score -= min(rejected_listings_count * 5, 20)

    if user.is_banned:
        score = 0

    # Keep score between 0 and 100
    score = max(0, min(score, 100))

    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.trust_score = score
    profile.save(update_fields=["trust_score"])

    return score