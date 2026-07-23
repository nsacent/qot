import json
import math

from django.db import transaction
from django.db.models import Count, F, Q
from django.utils.text import slugify
from .filters import ListingFilter

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Listing, ListingAttribute, ListingDraft, ListingImage, PendingListingImage
from apps.categories.models import Category, CategoryFilter
from .image_fingerprints import (
    validate_image_for_user,
    validate_staged_image_for_user,
)
from .image_processing import (
    delete_listing_image_files,
    generate_listing_variants,
    normalize_crop,
    prepare_listing_source,
    process_listing_upload,
)
from .permissions import IsListingOwnerOrReadOnly

from decimal import Decimal, InvalidOperation

from .serializers import (
    ListingListSerializer,
    ListingDetailSerializer,
    ListingCreateUpdateSerializer,
    ListingImageSerializer,
    ListingDraftSerializer,

)

from apps.common.permissions import IsNotBanned, IsVerifiedUser
from datetime import timedelta
from django.utils import timezone

from apps.searches.alerts import notify_saved_search_matches_for_listing


class ListingListCreateAPIView(generics.ListCreateAPIView):
    filterset_class = ListingFilter

    def get_permissions(self):
        if self.request.method == "POST":
            return [
                permissions.IsAuthenticated(),
                IsNotBanned(),
                IsVerifiedUser(),
            ]

        if self.request.query_params.get("mine") == "true":
            return [permissions.IsAuthenticated(), IsNotBanned()]

        return [permissions.AllowAny()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ListingCreateUpdateSerializer

        return ListingListSerializer

    def get_queryset(self):
        queryset = (
            Listing.objects
            .select_related(
                "seller",
                "category",
                "category__parent",
                "city",
                "city__region",
            )
            .prefetch_related(
                "images",
                "attributes",
                "attributes__category_filter__options",
            )
            .exclude(status=Listing.STATUS_DELETED)
            .order_by("-is_featured", "-created_at")
        )

        if self.request.user.is_authenticated:
            if self.request.query_params.get("mine") == "true":
                return queryset.filter(seller=self.request.user)

        return queryset.filter(
            status=Listing.STATUS_ACTIVE,
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        )

    def create(self, request, *args, **kwargs):
        if hasattr(request.data, "dict"):
            payload = request.data.dict()
        else:
            payload = dict(request.data)

        payload.pop("images", None)
        staged_image_ids = request.data.get("staged_image_ids", [])
        payload.pop("staged_image_ids", None)
        attributes = request.data.get("attributes", [])

        if isinstance(staged_image_ids, str):
            try:
                staged_image_ids = json.loads(staged_image_ids)
            except json.JSONDecodeError:
                return Response(
                    {"staged_image_ids": ["Staged image IDs must be valid JSON."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if not isinstance(staged_image_ids, list):
            return Response(
                {"staged_image_ids": ["Staged image IDs must be a list."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            staged_image_ids = [int(image_id) for image_id in staged_image_ids]
        except (TypeError, ValueError):
            return Response(
                {"staged_image_ids": ["Every staged image ID must be an integer."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(staged_image_ids) != len(set(staged_image_ids)):
            return Response(
                {"staged_image_ids": ["Staged image IDs cannot be duplicated."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if isinstance(attributes, str):
            try:
                parsed_attributes = json.loads(attributes)
            except json.JSONDecodeError:
                return Response(
                    {"attributes": ["Attributes must be valid JSON."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not isinstance(parsed_attributes, list):
                return Response(
                    {"attributes": ["Attributes must be a list."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            payload["attributes"] = parsed_attributes
        else:
            payload["attributes"] = attributes

        images = request.FILES.getlist("images")

        if len(images) + len(staged_image_ids) > 10:
            return Response(
                {"images": ["A listing can have a maximum of 10 images."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        validated_images = []
        seen_image_hashes = set()

        for image in images:
            image_serializer = ListingImageSerializer(data={"image": image})
            image_serializer.is_valid(raise_exception=True)
            validated_image = image_serializer.validated_data["image"]
            content_hash = validate_image_for_user(
                user=request.user,
                image_file=validated_image,
                seen_hashes=seen_image_hashes,
                error_field="images",
            )
            processed = process_listing_upload(validated_image)
            validated_images.append({
                "image": processed.detail,
                "source_image": processed.source,
                "card_image": processed.card,
                "social_image": processed.social,
                "content_hash": content_hash,
                "is_watermarked": True,
                "crop_x": 0.5,
                "crop_y": 0.5,
                "crop_zoom": 1.0,
            })

        serializer = self.get_serializer(data=payload)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            staged_images = list(
                PendingListingImage.objects.select_for_update().filter(
                    id__in=staged_image_ids,
                    user=request.user,
                )
            )

            staged_by_id = {image.id: image for image in staged_images}

            if len(staged_by_id) != len(set(staged_image_ids)):
                return Response(
                    {"staged_image_ids": ["One or more staged photos are invalid."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            staged_image_hashes = {}

            for image_id in staged_image_ids:
                staged_image_hashes[image_id] = validate_staged_image_for_user(
                    user=request.user,
                    image_record=staged_by_id[image_id],
                    seen_hashes=seen_image_hashes,
                    error_field="images",
                )

            listing = serializer.save()

            ordered_images = [{
                "image": staged_by_id[image_id].image.name,
                "source_image": staged_by_id[image_id].source_image.name,
                "card_image": staged_by_id[image_id].card_image.name,
                "social_image": staged_by_id[image_id].social_image.name,
                "content_hash": staged_image_hashes[image_id],
                "is_watermarked": staged_by_id[image_id].is_watermarked,
                "crop_x": staged_by_id[image_id].crop_x,
                "crop_y": staged_by_id[image_id].crop_y,
                "crop_zoom": staged_by_id[image_id].crop_zoom,
            } for image_id in staged_image_ids] + validated_images

            for index, image_data in enumerate(ordered_images):
                ListingImage.objects.create(
                    listing=listing,
                    is_primary=index == 0,
                    sort_order=index,
                    **image_data,
                )

            if staged_images:
                PendingListingImage.objects.filter(
                    id__in=staged_image_ids,
                    user=request.user,
                ).delete()

            base_slug = slugify(listing.title)
            listing.slug = f"{base_slug}-{listing.id}"
            listing.save(update_fields=["slug"])

        response_serializer = ListingDetailSerializer(
            listing,
            context={"request": request},
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )


def public_listing_queryset():
    return (
        Listing.objects
        .select_related("seller", "category", "category__parent", "city", "city__region")
        .filter(status=Listing.STATUS_ACTIVE)
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
    )


def filtered_listings(query_params, excluded_params=()):
    params = query_params.copy()
    for key in excluded_params:
        params.pop(key, None)
    return ListingFilter(params, queryset=public_listing_queryset()).qs


def rounded_price(value):
    value = max(int(value), 0)
    if value < 100_000:
        unit = 10_000
    elif value < 1_000_000:
        unit = 100_000
    elif value < 10_000_000:
        unit = 500_000
    elif value < 100_000_000:
        unit = 5_000_000
    else:
        unit = 10_000_000
    return max(unit, int(round(value / unit) * unit))


def price_label(value):
    if value >= 1_000_000_000:
        return f"UGX {value / 1_000_000_000:g}B"
    if value >= 1_000_000:
        return f"UGX {value / 1_000_000:g}M"
    if value >= 1_000:
        return f"UGX {value / 1_000:g}K"
    return f"UGX {value:,}"


class ListingFacetsAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        filtered = filtered_listings(request.query_params)
        price_queryset = filtered_listings(
            request.query_params,
            ("min_price", "max_price", "sort", "page", "page_size"),
        )
        prices = list(
            price_queryset.order_by("price").values_list("price", flat=True)[:5000]
        )
        price_presets = []
        if prices:
            indexes = [
                min(len(prices) - 1, math.floor((len(prices) - 1) * ratio))
                for ratio in (0.25, 0.5, 0.75)
            ]
            boundaries = sorted({rounded_price(prices[index]) for index in indexes})
            ranges = []
            if boundaries:
                ranges.append((None, boundaries[0]))
                ranges.extend(zip(boundaries, boundaries[1:]))
                ranges.append((boundaries[-1], None))
            for minimum, maximum in ranges:
                bucket = price_queryset
                if minimum is not None:
                    bucket = bucket.filter(price__gte=minimum)
                if maximum is not None:
                    bucket = bucket.filter(price__lt=maximum)
                count = bucket.count()
                if not count:
                    continue
                if minimum is None:
                    label = f"Under {price_label(maximum)}"
                elif maximum is None:
                    label = f"{price_label(minimum)} and above"
                else:
                    label = f"{price_label(minimum)} – {price_label(maximum)}"
                price_presets.append({
                    "label": label,
                    "min_price": minimum,
                    "max_price": maximum,
                    "count": count,
                })

        condition_base = filtered_listings(request.query_params, ("condition",))
        condition_counts = {
            item["condition"]: item["count"]
            for item in condition_base.values("condition").annotate(count=Count("id"))
        }
        city_base = filtered_listings(request.query_params, ("city",))
        city_counts = list(
            city_base.values(
                "city_id", "city__name", "city__slug",
                "city__region_id", "city__region__name", "city__region__slug",
            )
            .annotate(count=Count("id"))
            .order_by("-count", "city__name")[:100]
        )

        filter_facets = {}
        category_slug = request.query_params.get("category")
        category = Category.objects.filter(slug=category_slug, is_active=True).first()
        if category:
            category_filters = CategoryFilter.objects.filter(
                category=category,
                is_searchable=True,
            ).prefetch_related("options")
            for category_filter in category_filters:
                facet_base = filtered_listings(
                    request.query_params,
                    (category_filter.key, f"{category_filter.key}_min", f"{category_filter.key}_max"),
                )
                values = (
                    ListingAttribute.objects
                    .filter(
                        listing__in=facet_base,
                        category_filter=category_filter,
                        value_text__isnull=False,
                    )
                    .exclude(value_text="")
                    .values("value_text")
                    .annotate(count=Count("listing_id", distinct=True))
                    .order_by("-count", "value_text")[:40]
                )
                counts = {item["value_text"].lower(): item["count"] for item in values}
                options = [
                    {
                        "value": option.value,
                        "label": option.label,
                        "count": counts.get(option.value.lower(), 0),
                    }
                    for option in category_filter.options.filter(is_active=True)
                ]
                if not options and category_filter.filter_type in ("text", "select", "multi_select"):
                    options = [
                        {"value": item["value_text"], "label": item["value_text"], "count": item["count"]}
                        for item in values
                    ]
                filter_facets[category_filter.key] = {"options": options}

        return Response({
            "total_count": filtered.count(),
            "price_presets": price_presets,
            "condition_counts": condition_counts,
            "cities": city_counts,
            "filters": filter_facets,
        })


def pending_image_payload(pending_image, request):
    source_image = pending_image.source_image or pending_image.image
    card_image = pending_image.card_image or pending_image.image
    social_image = pending_image.social_image or card_image

    return {
        "id": pending_image.id,
        "image_url": request.build_absolute_uri(pending_image.image.url),
        "source_image_url": request.build_absolute_uri(source_image.url),
        "card_image_url": request.build_absolute_uri(card_image.url),
        "social_image_url": request.build_absolute_uri(social_image.url),
        "crop_x": pending_image.crop_x,
        "crop_y": pending_image.crop_y,
        "crop_zoom": pending_image.crop_zoom,
    }


class PendingListingImageAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBanned,
        IsVerifiedUser,
    ]

    def post(self, request):
        expired_images = PendingListingImage.objects.filter(
            user=request.user,
            reserved_for_draft=False,
            created_at__lt=timezone.now() - timedelta(hours=24),
        )

        for expired_image in expired_images:
            delete_listing_image_files(expired_image)
            expired_image.delete()

        image_serializer = ListingImageSerializer(data=request.data)
        image_serializer.is_valid(raise_exception=True)
        validated_image = image_serializer.validated_data["image"]
        crop_x, crop_y, crop_zoom = normalize_crop(
            image_serializer.validated_data.get("crop_x"),
            image_serializer.validated_data.get("crop_y"),
            image_serializer.validated_data.get("crop_zoom"),
        )
        content_hash = validate_image_for_user(
            user=request.user,
            image_file=validated_image,
            check_pending=True,
        )

        pending_count = PendingListingImage.objects.filter(user=request.user).count()

        if pending_count >= 10:
            return Response(
                {"detail": "You can stage a maximum of 10 photos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        processed = process_listing_upload(
            validated_image,
            crop_x,
            crop_y,
            crop_zoom,
        )
        pending_image = PendingListingImage.objects.create(
            user=request.user,
            image=processed.detail,
            source_image=processed.source,
            card_image=processed.card,
            social_image=processed.social,
            content_hash=content_hash,
            is_watermarked=True,
            crop_x=crop_x,
            crop_y=crop_y,
            crop_zoom=crop_zoom,
        )

        return Response(
            pending_image_payload(pending_image, request),
            status=status.HTTP_201_CREATED,
        )

    def patch(self, request, pk):
        pending_image = PendingListingImage.objects.filter(
            pk=pk,
            user=request.user,
        ).first()

        if not pending_image:
            return Response(
                {"detail": "Staged photo not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        crop_x, crop_y, crop_zoom = normalize_crop(
            request.data.get("crop_x", pending_image.crop_x),
            request.data.get("crop_y", pending_image.crop_y),
            request.data.get("crop_zoom", pending_image.crop_zoom),
        )
        old_variant_names = {
            pending_image.image.name,
            pending_image.card_image.name,
            pending_image.social_image.name,
        }

        if pending_image.source_image:
            source_image = pending_image.source_image
        else:
            source_image = prepare_listing_source(pending_image.image)
            pending_image.source_image = source_image

        variants = generate_listing_variants(
            source_image,
            crop_x,
            crop_y,
            crop_zoom,
        )
        pending_image.image = variants.detail
        pending_image.card_image = variants.card
        pending_image.social_image = variants.social
        pending_image.crop_x = crop_x
        pending_image.crop_y = crop_y
        pending_image.crop_zoom = crop_zoom
        pending_image.is_watermarked = True
        pending_image.save()

        new_names = {
            pending_image.image.name,
            pending_image.source_image.name,
            pending_image.card_image.name,
            pending_image.social_image.name,
        }
        for old_name in old_variant_names - new_names - {""}:
            pending_image.image.storage.delete(old_name)

        return Response(
            pending_image_payload(pending_image, request),
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk):
        pending_image = PendingListingImage.objects.filter(
            pk=pk,
            user=request.user,
        ).first()

        draft = ListingDraft.objects.filter(user=request.user).first()
        if draft:
            draft.staged_image_ids = [
                image_id
                for image_id in draft.staged_image_ids
                if str(image_id) != str(pk)
            ]
            draft.save(update_fields=["staged_image_ids", "updated_at"])

        if not pending_image:
            return Response(status=status.HTTP_204_NO_CONTENT)

        delete_listing_image_files(pending_image)
        pending_image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ListingDraftAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBanned,
        IsVerifiedUser,
    ]

    allowed_data_fields = {
        "title",
        "description",
        "price",
        "category",
        "city",
        "condition",
        "is_negotiable",
        "category_filter_values",
    }

    def get(self, request):
        draft = ListingDraft.objects.filter(user=request.user).first()

        if not draft:
            return Response({"draft": None}, status=status.HTTP_200_OK)

        serializer = ListingDraftSerializer(
            draft,
            context={"request": request},
        )
        return Response({"draft": serializer.data}, status=status.HTTP_200_OK)

    @transaction.atomic
    def put(self, request):
        raw_data = request.data.get("data", {})
        staged_image_ids = request.data.get("staged_image_ids", [])

        if not isinstance(raw_data, dict):
            return Response(
                {"data": ["Draft data must be an object."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        unknown_fields = set(raw_data) - self.allowed_data_fields
        if unknown_fields:
            return Response(
                {"data": [f"Unknown draft field: {sorted(unknown_fields)[0]}."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(staged_image_ids, list):
            return Response(
                {"staged_image_ids": ["Staged image IDs must be a list."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            staged_image_ids = [int(image_id) for image_id in staged_image_ids]
        except (TypeError, ValueError):
            return Response(
                {"staged_image_ids": ["Every staged image ID must be an integer."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(staged_image_ids) != len(set(staged_image_ids)):
            return Response(
                {"staged_image_ids": ["Staged image IDs cannot be duplicated."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        owned_image_ids = set(
            PendingListingImage.objects.filter(
                user=request.user,
                id__in=staged_image_ids,
            ).values_list("id", flat=True)
        )
        if owned_image_ids != set(staged_image_ids):
            return Response(
                {"staged_image_ids": ["One or more staged photos are invalid."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        draft, _ = ListingDraft.objects.select_for_update().get_or_create(
            user=request.user,
        )
        old_image_ids = set(draft.staged_image_ids)
        new_image_ids = set(staged_image_ids)

        PendingListingImage.objects.filter(
            user=request.user,
            id__in=old_image_ids - new_image_ids,
        ).update(reserved_for_draft=False)
        PendingListingImage.objects.filter(
            user=request.user,
            id__in=new_image_ids,
        ).update(reserved_for_draft=True)

        draft.data = raw_data
        draft.staged_image_ids = staged_image_ids
        draft.save()

        serializer = ListingDraftSerializer(
            draft,
            context={"request": request},
        )
        return Response({"draft": serializer.data}, status=status.HTTP_200_OK)

    @transaction.atomic
    def delete(self, request):
        draft = ListingDraft.objects.select_for_update().filter(user=request.user).first()

        if draft:
            PendingListingImage.objects.filter(
                user=request.user,
                id__in=draft.staged_image_ids,
            ).update(reserved_for_draft=False)
            draft.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class ListingDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]

        return [
            permissions.IsAuthenticated(),
            IsNotBanned(),
            IsVerifiedUser(),
            IsListingOwnerOrReadOnly(),
        ]

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return ListingCreateUpdateSerializer

        return ListingDetailSerializer

    def get_queryset(self):
        queryset = (
            Listing.objects
            .select_related("seller", "category", "category__parent", "city")
            .prefetch_related(
                "images",
                "attributes",
                "attributes__category_filter__options",
            )
            .exclude(status=Listing.STATUS_DELETED)
        )

        if self.request.method not in permissions.SAFE_METHODS:
            return queryset

        public_listings = Q(status=Listing.STATUS_ACTIVE) & (
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        )

        user = self.request.user

        if user.is_authenticated:
            if user.is_staff or getattr(user, "role", "") in {"admin", "moderator"}:
                return queryset

            return queryset.filter(Q(seller=user) | public_listings)

        return queryset.filter(public_listings)

    def retrieve(self, request, *args, **kwargs):
        listing = self.get_object()

        if listing.status == Listing.STATUS_ACTIVE:
            Listing.objects.filter(pk=listing.pk).update(
                views_count=F("views_count") + 1
            )
            listing.refresh_from_db(fields=["views_count"])

        serializer = self.get_serializer(listing)
        return Response(serializer.data)

    def perform_destroy(self, instance):
        instance.soft_delete()


class MarkListingSoldAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBanned,
        IsVerifiedUser,
    ]

    def post(self, request, pk):
        try:
            listing = Listing.objects.get(
                pk=pk,
                seller=request.user,
            )
        except Listing.DoesNotExist:
            return Response(
                {"detail": "Listing not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        allowed_statuses = {
            Listing.STATUS_ACTIVE,
            Listing.STATUS_UNAVAILABLE,
        }

        if listing.status not in allowed_statuses:
            return Response(
                {
                    "detail": (
                        "Only approved active or unavailable listings can be marked "
                        "as sold. Pending and rejected listings require moderation."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        listing.status = Listing.STATUS_SOLD
        listing.sold_at = timezone.now()
        listing.save(update_fields=["status", "sold_at", "updated_at"])

        return Response(
            {
                "message": "Listing marked as sold successfully.",
                "listing_id": listing.id,
                "status": listing.status,
                "sold_at": listing.sold_at,
            },
            status=status.HTTP_200_OK,
        )

class MarkListingAvailableAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBanned,
        IsVerifiedUser,
    ]

    def post(self, request, pk):
        try:
            listing = Listing.objects.get(
                pk=pk,
                seller=request.user,
            )
        except Listing.DoesNotExist:
            return Response(
                {"detail": "Listing not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        allowed_statuses = {
            Listing.STATUS_UNAVAILABLE,
            Listing.STATUS_SOLD,
        }

        if listing.status not in allowed_statuses:
            return Response(
                {
                    "detail": (
                        "Only sold or unavailable listings can be marked available. "
                        "Pending and rejected listings require moderation."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        listing.status = Listing.STATUS_ACTIVE
        listing.sold_at = None

        if not listing.expires_at or listing.expires_at <= timezone.now():
            listing.expires_at = timezone.now() + timedelta(days=30)

        listing.save(
            update_fields=[
                "status",
                "sold_at",
                "expires_at",
                "updated_at",
            ]
        )

        return Response(
            {
                "message": "Listing marked as available successfully.",
                "listing_id": listing.id,
                "status": listing.status,
            },
            status=status.HTTP_200_OK,
        )

class MarkListingUnavailableAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBanned,
        IsVerifiedUser,
    ]

    def post(self, request, pk):
        try:
            listing = Listing.objects.get(
                pk=pk,
                seller=request.user,
            )
        except Listing.DoesNotExist:
            return Response(
                {"detail": "Listing not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if listing.status != Listing.STATUS_ACTIVE:
            return Response(
                {"detail": "Only active listings can be marked unavailable."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        listing.status = Listing.STATUS_UNAVAILABLE
        listing.save(update_fields=["status", "updated_at"])

        return Response(
            {
                "message": "Listing marked as unavailable successfully.",
                "listing_id": listing.id,
                "status": listing.status,
            },
            status=status.HTTP_200_OK,
        )
    

class RelistListingAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBanned,
        IsVerifiedUser,
    ]

    def post(self, request, pk):
        try:
            listing = Listing.objects.get(
                pk=pk,
                seller=request.user,
            )
        except Listing.DoesNotExist:
            return Response(
                {"detail": "Listing not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        allowed_statuses = {
            Listing.STATUS_EXPIRED,
            Listing.STATUS_UNAVAILABLE,
            Listing.STATUS_SOLD,
        }

        if listing.status not in allowed_statuses:
            return Response(
                {
                    "detail": (
                        "Only expired, unavailable, or sold listings can be relisted. "
                        "Pending and rejected listings require moderation."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        listing.status = Listing.STATUS_ACTIVE
        listing.sold_at = None
        listing.expires_at = timezone.now() + timedelta(days=30)

        listing.save(
            update_fields=[
                "status",
                "sold_at",
                "expires_at",
                "updated_at",
            ]
        )

        notify_saved_search_matches_for_listing(listing)

        return Response(
            {
                "message": "Listing relisted successfully.",
                "listing_id": listing.id,
                "status": listing.status,
                "expires_at": listing.expires_at,
            },
            status=status.HTTP_200_OK,
        )


class RenewListingAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBanned,
        IsVerifiedUser,
    ]

    def post(self, request, pk):
        try:
            listing = Listing.objects.get(
                pk=pk,
                seller=request.user,
            )
        except Listing.DoesNotExist:
            return Response(
                {"detail": "Listing not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        allowed_statuses = {
            Listing.STATUS_ACTIVE,
            Listing.STATUS_EXPIRED,
        }

        if listing.status not in allowed_statuses:
            return Response(
                {
                    "detail": (
                        "Only active or expired listings can be renewed. "
                        "Pending and rejected listings require moderation."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        listing.status = Listing.STATUS_ACTIVE
        listing.expires_at = timezone.now() + timedelta(days=30)
        listing.sold_at = None

        listing.save(
            update_fields=[
                "status",
                "expires_at",
                "sold_at",
                "updated_at",
            ]
        )

        notify_saved_search_matches_for_listing(listing)

        return Response(
            {
                "message": "Listing renewed successfully.",
                "listing_id": listing.id,
                "status": listing.status,
                "expires_at": listing.expires_at,
            },
            status=status.HTTP_200_OK,
        )



class ListingImageUploadAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBanned,
        IsVerifiedUser,
    ]

    def post(self, request, pk):
        try:
            listing = Listing.objects.get(
                pk=pk,
                seller=request.user,
            )
        except Listing.DoesNotExist:
            return Response(
                {"detail": "Listing not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        current_images_count = listing.images.count()

        if current_images_count >= 10:
            return Response(
                {"detail": "A listing can have a maximum of 10 images."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ListingImageSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        validated_image = serializer.validated_data["image"]
        crop_x, crop_y, crop_zoom = normalize_crop(
            serializer.validated_data.get("crop_x"),
            serializer.validated_data.get("crop_y"),
            serializer.validated_data.get("crop_zoom"),
        )
        content_hash = validate_image_for_user(
            user=request.user,
            image_file=validated_image,
        )

        is_first_image = current_images_count == 0
        processed = process_listing_upload(
            validated_image,
            crop_x,
            crop_y,
            crop_zoom,
        )

        image = serializer.save(
            listing=listing,
            image=processed.detail,
            source_image=processed.source,
            card_image=processed.card,
            social_image=processed.social,
            content_hash=content_hash,
            is_watermarked=True,
            is_primary=is_first_image,
            sort_order=current_images_count,
            crop_x=crop_x,
            crop_y=crop_y,
            crop_zoom=crop_zoom,
        )

        response_serializer = ListingImageSerializer(
            image,
            context={"request": request},
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )





class CropListingImageAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBanned,
        IsVerifiedUser,
    ]

    def patch(self, request, pk, image_id):
        try:
            listing = Listing.objects.get(pk=pk, seller=request.user)
        except Listing.DoesNotExist:
            return Response(
                {"detail": "Listing not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            image = listing.images.get(pk=image_id)
        except ListingImage.DoesNotExist:
            return Response(
                {"detail": "Image not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        crop_x, crop_y, crop_zoom = normalize_crop(
            request.data.get("crop_x", image.crop_x),
            request.data.get("crop_y", image.crop_y),
            request.data.get("crop_zoom", image.crop_zoom),
        )
        old_variant_names = {
            image.image.name,
            image.card_image.name,
            image.social_image.name,
        }

        if image.source_image:
            source_image = image.source_image
        else:
            source_image = prepare_listing_source(image.image)
            image.source_image = source_image

        variants = generate_listing_variants(
            source_image,
            crop_x,
            crop_y,
            crop_zoom,
        )
        image.image = variants.detail
        image.card_image = variants.card
        image.social_image = variants.social
        image.crop_x = crop_x
        image.crop_y = crop_y
        image.crop_zoom = crop_zoom
        image.is_watermarked = True
        image.save()

        new_names = {
            image.image.name,
            image.source_image.name,
            image.card_image.name,
            image.social_image.name,
        }
        for old_name in old_variant_names - new_names - {""}:
            image.image.storage.delete(old_name)

        return Response(
            ListingImageSerializer(image, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


class ListingImageDeleteAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBanned,
        IsVerifiedUser,
    ]

    def delete(self, request, pk, image_id):
        try:
            listing = Listing.objects.get(
                pk=pk,
                seller=request.user,
            )
        except Listing.DoesNotExist:
            return Response(
                {"detail": "Listing not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            image = listing.images.get(pk=image_id)
        except ListingImage.DoesNotExist:
            return Response(
                {"detail": "Image not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        was_primary = image.is_primary

        delete_listing_image_files(image)
        image.delete()

        if was_primary:
            next_image = listing.images.order_by("sort_order", "id").first()

            if next_image:
                next_image.is_primary = True
                next_image.save(update_fields=["is_primary"])

        return Response(
            {"message": "Image deleted successfully."},
            status=status.HTTP_200_OK,
        )




class SetPrimaryListingImageAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBanned,
        IsVerifiedUser,
    ]

    def post(self, request, pk, image_id):
        try:
            listing = Listing.objects.get(
                pk=pk,
                seller=request.user,
            )
        except Listing.DoesNotExist:
            return Response(
                {"detail": "Listing not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            image = listing.images.get(pk=image_id)
        except ListingImage.DoesNotExist:
            return Response(
                {"detail": "Image not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        listing.images.update(is_primary=False)

        image.is_primary = True
        image.save(update_fields=["is_primary"])

        return Response(
            {
                "message": "Primary image updated successfully.",
                "image_id": image.id,
            },
            status=status.HTTP_200_OK,
        )


class ReorderListingImagesAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBanned,
        IsVerifiedUser,
    ]

    def post(self, request, pk):
        try:
            listing = Listing.objects.get(pk=pk, seller=request.user)
        except Listing.DoesNotExist:
            return Response(
                {"detail": "Listing not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        image_ids = request.data.get("image_ids")

        if not isinstance(image_ids, list) or not image_ids:
            return Response(
                {"detail": "Provide the complete photo order."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            normalized_ids = [int(image_id) for image_id in image_ids]
        except (TypeError, ValueError):
            return Response(
                {"detail": "Photo order contains an invalid image."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        current_ids = list(listing.images.values_list("id", flat=True))

        if (
            len(normalized_ids) != len(set(normalized_ids))
            or set(normalized_ids) != set(current_ids)
        ):
            return Response(
                {"detail": "Photo order must include every ad photo exactly once."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        images_by_id = {
            image.id: image
            for image in listing.images.filter(id__in=normalized_ids)
        }

        with transaction.atomic():
            for sort_order, image_id in enumerate(normalized_ids):
                image = images_by_id[image_id]
                image.sort_order = sort_order
                image.is_primary = sort_order == 0

            ListingImage.objects.bulk_update(
                images_by_id.values(),
                ["sort_order", "is_primary"],
            )

        return Response(
            {
                "message": "Photo order updated successfully.",
                "image_ids": normalized_ids,
                "primary_image_id": normalized_ids[0],
            },
            status=status.HTTP_200_OK,
        )
