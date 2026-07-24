from datetime import timedelta

from django.utils import timezone
from PIL import Image
from rest_framework import serializers

from .image_processing import MIN_IMAGE_SIZE
from .models import Listing, ListingDraft, ListingImage, ListingAttribute, PendingListingImage


class ListingImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    source_image_url = serializers.SerializerMethodField()
    card_image_url = serializers.SerializerMethodField()
    social_image_url = serializers.SerializerMethodField()

    class Meta:
        model = ListingImage
        fields = [
            "id",
            "image",
            "image_url",
            "source_image_url",
            "card_image_url",
            "social_image_url",
            "is_primary",
            "sort_order",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "image_url",
            "source_image_url",
            "card_image_url",
            "social_image_url",
            "is_primary",
            "created_at",
        ]

    def _absolute_url(self, field):
        if not field:
            return None

        request = self.context.get("request")

        if request:
            return request.build_absolute_uri(field.url)

        return field.url

    def get_image_url(self, obj):
        return self._absolute_url(obj.image)

    def get_source_image_url(self, obj):
        request = self.context.get("request")
        request_user = getattr(request, "user", None)

        if not request_user or not request_user.is_authenticated:
            return None

        if request_user != obj.listing.seller and not request_user.is_staff:
            return None

        return self._absolute_url(obj.source_image or obj.image)

    def get_card_image_url(self, obj):
        return self._absolute_url(obj.card_image or obj.image)

    def get_social_image_url(self, obj):
        return self._absolute_url(obj.social_image or obj.card_image or obj.image)

    def validate_image(self, image):
        max_size = 8 * 1024 * 1024

        if image.size > max_size:
            raise serializers.ValidationError(
                "Image size must not exceed 8MB."
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

            minimum_width, minimum_height = MIN_IMAGE_SIZE
            width, height = img.size

            if (
                min(width, height) < min(minimum_width, minimum_height)
                or max(width, height) < max(minimum_width, minimum_height)
            ):
                raise serializers.ValidationError(
                    "Image resolution must be at least 600 × 450 pixels."
                )
        except serializers.ValidationError:
            raise
        except Exception:
            raise serializers.ValidationError(
                "Uploaded file is not a valid image."
            )

        image.seek(0)

        return image


class ListingDraftSerializer(serializers.ModelSerializer):
    staged_images = serializers.SerializerMethodField()

    class Meta:
        model = ListingDraft
        fields = [
            "id",
            "data",
            "staged_image_ids",
            "staged_images",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_staged_images(self, obj):
        images = PendingListingImage.objects.filter(
            user=obj.user,
            id__in=obj.staged_image_ids,
        )
        images_by_id = {image.id: image for image in images}
        request = self.context.get("request")
        result = []

        for image_id in obj.staged_image_ids:
            image = images_by_id.get(image_id)
            if not image or not image.image:
                continue

            image_url = image.image.url
            if request:
                image_url = request.build_absolute_uri(image_url)

            source_field = image.source_image or image.image
            card_field = image.card_image or image.image
            source_url = source_field.url
            card_url = card_field.url
            if request:
                source_url = request.build_absolute_uri(source_url)
                card_url = request.build_absolute_uri(card_url)

            result.append({
                "id": image.id,
                "image_url": image_url,
                "source_image_url": source_url,
                "card_image_url": card_url,
            })

        return result


class ListingAttributeSerializer(serializers.ModelSerializer):
    category_filter_id = serializers.IntegerField(
        source="category_filter.id",
        read_only=True,
    )
    filter_name = serializers.CharField(
        source="category_filter.name",
        read_only=True,
    )
    filter_key = serializers.CharField(
        source="category_filter.key",
        read_only=True,
    )
    filter_type = serializers.CharField(
        source="category_filter.filter_type",
        read_only=True,
    )
    display_value = serializers.SerializerMethodField()

    def get_display_value(self, obj):
        if obj.value_text is None:
            return None

        raw_value = str(obj.value_text).strip()

        if not raw_value:
            return None

        options = list(obj.category_filter.options.all())

        for option in options:
            if str(option.value) == raw_value:
                return option.label

        if raw_value.isdigit():
            for option in options:
                if option.id == int(raw_value):
                    return option.label

        return None

    class Meta:
        model = ListingAttribute
        fields = [
            "id",
            "category_filter_id",
            "filter_name",
            "filter_key",
            "filter_type",
            "display_value",
            "value_text",
            "value_number",
            "value_boolean",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "category_filter_id",
            "filter_name",
            "filter_key",
            "filter_type",
            "display_value",
            "created_at",
        ]


class ListingAttributeInputSerializer(serializers.Serializer):
    category_filter_id = serializers.IntegerField()
    value_text = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    value_number = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True,
    )
    value_boolean = serializers.BooleanField(
        required=False,
        allow_null=True,
    )


class ListingListSerializer(serializers.ModelSerializer):
    seller_name = serializers.CharField(
        source="seller.full_name",
        read_only=True,
    )
    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
    )
    category_parent_name = serializers.SerializerMethodField()
    city_name = serializers.CharField(
        source="city.name",
        read_only=True,
    )
    primary_image = serializers.SerializerMethodField()
    image_count = serializers.SerializerMethodField()


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
            "category_parent_name",
            "city",
            "city_name",
            "price",
            "currency",
            "condition",
            "status",
            "is_negotiable",
            "is_featured",
            "featured_until",
            "views_count",
            "favorites_count",
            "image_count",
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
            "featured_until",
            "created_at",
        ]

    def get_category_parent_name(self, obj):
        parent = getattr(obj.category, "parent", None)
        return parent.name if parent else None

    def get_primary_image(self, obj):
        image = obj.images.filter(is_primary=True).first() or obj.images.first()

        if not image or not image.image:
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


class ListingDetailSerializer(serializers.ModelSerializer):
    seller_name = serializers.CharField(
        source="seller.full_name",
        read_only=True,
    )
    seller_phone = serializers.CharField(
        source="seller.phone",
        read_only=True,
    )
    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
    )
    category_parent_name = serializers.SerializerMethodField()
    city_name = serializers.CharField(
        source="city.name",
        read_only=True,
    )

    images = ListingImageSerializer(many=True, read_only=True)
    attributes = serializers.SerializerMethodField()
    image_count = serializers.SerializerMethodField()

    def get_image_count(self, obj):
        annotated_count = getattr(obj, "image_count", None)
        if annotated_count is not None:
            return annotated_count
        return obj.images.count()

    def get_attributes(self, obj):
        attributes = obj.attributes.filter(
            category_filter__is_searchable=True,
        ).select_related("category_filter").prefetch_related(
            "category_filter__options"
        )
        return ListingAttributeSerializer(attributes, many=True).data

    def get_category_parent_name(self, obj):
        parent = getattr(obj.category, "parent", None)
        return parent.name if parent else None

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
            "category_parent_name",
            "city",
            "city_name",
            "description",
            "price",
            "currency",
            "condition",
            "status",
            "is_negotiable",
            "is_featured",
            "featured_until",
            "views_count",
            "favorites_count",
            "expires_at",
            "sold_at",
            "rejection_reason",
            "images",
            "image_count",
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
            "featured_until",
            "updated_at",

        ]


class ListingCreateUpdateSerializer(serializers.ModelSerializer):
    attributes = ListingAttributeInputSerializer(
        many=True,
        required=False,
        write_only=True,
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
            raise serializers.ValidationError(
                "Price must be greater than zero."
            )

        return value

    def create(self, validated_data):
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
            category_filter_id = item.get("category_filter_id")

            try:
                category_filter = CategoryFilter.objects.get(
                    id=category_filter_id,
                    category=listing.category,
                    is_searchable=True,
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

            if value_text is not None:
                value_text = str(value_text).strip()

                options = list(
                    category_filter.options.filter(is_active=True)
                )

                if options:
                    selected_option = next(
                        (
                            option
                            for option in options
                            if str(option.value) == value_text
                        ),
                        None,
                    )

                    if selected_option is None and value_text.isdigit():
                        selected_option = next(
                            (
                                option
                                for option in options
                                if option.id == int(value_text)
                            ),
                            None,
                        )

                    if selected_option is None:
                        raise serializers.ValidationError(
                            {
                                "attributes": [
                                    f"Invalid option for {category_filter.name}."
                                ]
                            }
                        )

                    value_text = selected_option.value

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
