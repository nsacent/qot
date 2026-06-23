from rest_framework import serializers
from .models import Listing, ListingImage, ListingAttribute
from datetime import timedelta
from django.utils import timezone
from PIL import Image

class ListingImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ListingImage
        fields = [
            "id",
            "image",
            "image_url",
            "is_primary",
            "sort_order",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "image_url",
            "is_primary",
            "created_at",
        ]

    def get_image_url(self, obj):
        if not obj.image:
            return None

        request = self.context.get("request")

        if request:
            return request.build_absolute_uri(obj.image.url)

        return obj.image.url

    def validate_image(self, image):
        max_size = 5 * 1024 * 1024

        if image.size > max_size:
            raise serializers.ValidationError(
                "Image size must not exceed 5MB."
            )

        allowed_extensions = ["jpg", "jpeg", "png", "webp"]
        allowed_formats = ["JPEG", "PNG", "WEBP"]

        extension = image.name.split(".")[-1].lower()

        if extension not in allowed_extensions:
            raise serializers.ValidationError(
                "Only JPG, JPEG, PNG, and WEBP images are allowed."
            )

        try:
            img = Image.open(image)
            img.verify()
        except Exception:
            raise serializers.ValidationError(
                "Uploaded file is not a valid image."
            )

        image.seek(0)

        try:
            img = Image.open(image)

            if img.format not in allowed_formats:
                raise serializers.ValidationError(
                    "Only JPG, JPEG, PNG, and WEBP images are allowed."
                )
        except serializers.ValidationError:
            raise
        except Exception:
            raise serializers.ValidationError(
                "Uploaded file is not a valid image."
            )

        image.seek(0)

        return image


class ListingAttributeSerializer(serializers.ModelSerializer):
    filter_name = serializers.CharField(source="category_filter.name", read_only=True)
    filter_key = serializers.CharField(source="category_filter.key", read_only=True)
    filter_type = serializers.CharField(source="category_filter.filter_type", read_only=True)

    class Meta:
        model = ListingAttribute
        fields = [
            "id",
            "category_filter",
            "filter_name",
            "filter_key",
            "filter_type",
            "value_text",
            "value_number",
            "value_boolean",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "filter_name",
            "filter_key",
            "filter_type",
            "created_at",
        ]


class ListingAttributeInputSerializer(serializers.Serializer):
    category_filter = serializers.IntegerField()
    value_text = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    value_number = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True,
    )
    value_boolean = serializers.BooleanField(required=False, allow_null=True)



class ListingListSerializer(serializers.ModelSerializer):
    seller_name = serializers.CharField(source="seller.full_name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            "id",
            "title",
            "slug",
            "seller",
            "seller_name",
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
            "primary_image",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "seller",
            "slug",
            "status",
            "views_count",
            "favorites_count",
            "created_at",
        ]

    def get_primary_image(self, obj):
        image = obj.images.filter(is_primary=True).first() or obj.images.first()

        if image and image.image:
            request = self.context.get("request")
            image_url = image.image.url

            if request:
                return request.build_absolute_uri(image_url)

            return image_url

        return None


class ListingDetailSerializer(serializers.ModelSerializer):
    seller_name = serializers.CharField(source="seller.full_name", read_only=True)
    seller_phone = serializers.CharField(source="seller.phone", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)

    images = ListingImageSerializer(many=True, read_only=True)
    attributes = ListingAttributeSerializer(many=True, read_only=True)

    class Meta:
        model = Listing
        fields = [
            "id",
            "title",
            "slug",
            "seller",
            "seller_name",
            "seller_phone",
            "category",
            "category_name",
            "city",
            "city_name",
            "description",
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
            "images",
            "attributes",
            "created_at",
            "updated_at",

        ]
        read_only_fields = [
            "id",
            "seller",
            "slug",
            "status",
            "views_count",
            "favorites_count",
            "sold_at",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]


class ListingCreateUpdateSerializer(serializers.ModelSerializer):

    attributes = ListingAttributeInputSerializer(
    many=True,
    required=False,
)
    class Meta:
        model = Listing
        fields = [
            "id",
            "category",
            "city",
            "title",
            "description",
            "price",
            "currency",
            "condition",
            "is_negotiable",
            "attributes",
        ]

        read_only_fields = [
            "id",
        ]

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than zero.")

        return value

    def create(self, validated_data):
        from datetime import timedelta
        from django.utils import timezone

        attributes_data = validated_data.pop("attributes", [])
        request = self.context["request"]

        listing = Listing.objects.create(
            seller=request.user,
            status=Listing.STATUS_PENDING,
            expires_at=timezone.now() + timedelta(days=30),
            **validated_data,
        )

        self._save_attributes(listing, attributes_data)

        return listing
    

    def update(self, instance, validated_data):
        attributes_data = validated_data.pop("attributes", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.status = Listing.STATUS_PENDING
        instance.rejection_reason = ""
        instance.save()

        if attributes_data is not None:
            instance.attributes.all().delete()
            self._save_attributes(instance, attributes_data)

        return instance
    
    def _save_attributes(self, listing, attributes_data):
        from apps.categories.models import CategoryFilter

        for item in attributes_data:
            category_filter_id = item.get("category_filter")

            try:
                category_filter = CategoryFilter.objects.get(
                    id=category_filter_id,
                    category=listing.category,
                )
            except CategoryFilter.DoesNotExist:
                raise serializers.ValidationError(
                    {
                        "attributes": [
                            f"Invalid category filter ID: {category_filter_id}"
                        ]
                    }
                )

            value_text = item.get("value_text")
            value_number = item.get("value_number")
            value_boolean = item.get("value_boolean")

            if category_filter.filter_type in ["text", "select", "multi_select"]:
                if not value_text:
                    raise serializers.ValidationError(
                        {
                            "attributes": [
                                f"{category_filter.name} requires a text value."
                            ]
                        }
                    )

            if category_filter.filter_type == "number":
                if value_number is None:
                    raise serializers.ValidationError(
                        {
                            "attributes": [
                                f"{category_filter.name} requires a number value."
                            ]
                        }
                    )

            if category_filter.filter_type == "boolean":
                if value_boolean is None:
                    raise serializers.ValidationError(
                        {
                            "attributes": [
                                f"{category_filter.name} requires a true or false value."
                            ]
                        }
                    )

            ListingAttribute.objects.create(
                listing=listing,
                category_filter=category_filter,
                value_text=value_text,
                value_number=value_number,
                value_boolean=value_boolean,
            )