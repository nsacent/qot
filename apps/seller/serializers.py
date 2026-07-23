from rest_framework import serializers

from apps.listings.models import Listing


class SellerListingSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    primary_image = serializers.SerializerMethodField()
    image_count = serializers.SerializerMethodField()

    
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
            "status",
            "is_negotiable",
            "is_featured",
            "views_count",
            "favorites_count",
            "expires_at",
            "sold_at",
            "rejection_reason",
            "created_at",
            "updated_at",
            "primary_image",
            "image_count",
        ]

    def get_primary_image(self, obj):
        image = obj.images.filter(is_primary=True).first() or obj.images.first()

        if not image:
            return None

        display_image = image.card_image or image.image
        request = self.context.get("request")

        if request:
            return request.build_absolute_uri(display_image.url)

        return display_image.url
    
    def get_image_count(self, obj):
        annotated_count = getattr(obj, "image_count", None)

        if annotated_count is not None:
            return annotated_count

        return obj.images.count()

    

class SellerAnalyticsSummarySerializer(serializers.Serializer):
    total_listings = serializers.IntegerField()
    active_listings = serializers.IntegerField()
    sold_listings = serializers.IntegerField()
    expired_listings = serializers.IntegerField()
    unavailable_listings = serializers.IntegerField()
    total_views = serializers.IntegerField()
    total_favorites = serializers.IntegerField()
    total_chat_threads = serializers.IntegerField()


class SellerListingAnalyticsSerializer(serializers.Serializer):
    listing_id = serializers.IntegerField()
    title = serializers.CharField()
    status = serializers.CharField()
    price = serializers.DecimalField(max_digits=12, decimal_places=2)
    views_count = serializers.IntegerField()
    favorites_count = serializers.IntegerField()
    chat_threads_count = serializers.IntegerField()
    is_featured = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    expires_at = serializers.DateTimeField(allow_null=True)


class SellerDashboardListingMiniSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    status = serializers.CharField()
    price = serializers.DecimalField(max_digits=12, decimal_places=2)
    views_count = serializers.IntegerField()
    favorites_count = serializers.IntegerField()
    is_featured = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    expires_at = serializers.DateTimeField(allow_null=True)


class SellerDashboardSummarySerializer(serializers.Serializer):
    total_listings = serializers.IntegerField()
    active_listings = serializers.IntegerField()
    pending_listings = serializers.IntegerField()
    sold_listings = serializers.IntegerField()
    expired_listings = serializers.IntegerField()
    unavailable_listings = serializers.IntegerField()

    total_views = serializers.IntegerField()
    total_favorites = serializers.IntegerField()
    total_chat_threads = serializers.IntegerField()

    active_featured_listings = serializers.IntegerField()
    listings_needing_renewal = serializers.IntegerField()

    best_listing = SellerDashboardListingMiniSerializer(allow_null=True)
    weakest_listing = SellerDashboardListingMiniSerializer(allow_null=True)
    recent_listings = SellerDashboardListingMiniSerializer(many=True)
