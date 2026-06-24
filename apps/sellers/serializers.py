from rest_framework import serializers

from apps.accounts.models import User
from apps.listings.models import Listing
from django.db.models import Avg


class PublicSellerSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()
    bio = serializers.CharField(source="profile.bio", read_only=True)
    business_name = serializers.CharField(source="profile.business_name", read_only=True)
    trust_score = serializers.IntegerField(source="profile.trust_score", read_only=True)
    total_active_listings = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    total_reviews = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "full_name",
            "phone",
            "avatar",
            "bio",
            "business_name",
            "trust_score",
            "average_rating",
            "total_reviews",
            "total_active_listings",
            "date_joined",
        ]

    def get_avatar(self, obj):
        profile = getattr(obj, "profile", None)

        if not profile or not profile.avatar:
            return None

        request = self.context.get("request")

        if request:
            return request.build_absolute_uri(profile.avatar.url)

        return profile.avatar.url

    def get_total_active_listings(self, obj):
        return obj.listings.filter(status=Listing.STATUS_ACTIVE).count()

    def get_average_rating(self, obj):
        average = obj.received_reviews.filter(
            is_visible=True,
        ).aggregate(
            average=Avg("rating"),
        )["average"]

        return round(average or 0, 1)

    def get_total_reviews(self, obj):
        return obj.received_reviews.filter(
            is_visible=True,
        ).count()

class PublicSellerListingSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            "id",
            "title",
            "slug",
            "category",
            "category_name",
            "city",
            "city_name",
            "price",
            "currency",
            "condition",
            "is_negotiable",
            "is_featured",
            "views_count",
            "favorites_count",
            "created_at",
            "primary_image",
        ]

    def get_primary_image(self, obj):
        image = obj.images.filter(is_primary=True).first() or obj.images.first()

        if not image:
            return None

        request = self.context.get("request")

        if request:
            return request.build_absolute_uri(image.image.url)

        return image.image.url