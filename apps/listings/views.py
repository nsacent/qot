import json

from django.db import transaction
from django.db.models import F,Q
from django.utils.text import slugify
from .filters import ListingFilter

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Listing, ListingImage, PendingListingImage
from .permissions import IsListingOwnerOrReadOnly

from decimal import Decimal, InvalidOperation

from .serializers import (
    ListingListSerializer,
    ListingDetailSerializer,
    ListingCreateUpdateSerializer,
    ListingImageSerializer,

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
            .prefetch_related("images", "attributes")
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

        for image in images:
            image_serializer = ListingImageSerializer(data={"image": image})
            image_serializer.is_valid(raise_exception=True)
            validated_images.append(image_serializer.validated_data["image"])

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

            listing = serializer.save()

            ordered_images = [
                staged_by_id[image_id].image.name
                for image_id in staged_image_ids
            ] + validated_images

            for index, image in enumerate(ordered_images):
                ListingImage.objects.create(
                    listing=listing,
                    image=image,
                    is_primary=index == 0,
                    sort_order=index,
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

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)

        reserved_params = {
            "page",
            "page_size",
            "q",
            "search",
            "category",
            "city",
            "region",
            "min_price",
            "max_price",
            "condition",
            "status",
            "seller",
            "sort",
            "mine",
            "is_negotiable",
            "negotiable",
        }

        negotiable_value = (
            self.request.query_params.get("is_negotiable")
            or self.request.query_params.get("negotiable")
        )

        if negotiable_value is not None and negotiable_value != "":
            value = str(negotiable_value).strip().lower()

            if value in ["true", "1", "yes", "on"]:
                queryset = queryset.filter(is_negotiable=True)

            elif value in ["false", "0", "no", "off"]:
                queryset = queryset.filter(is_negotiable=False)

        for key, value in self.request.query_params.items():
            if key in reserved_params:
                continue

            if value is None or value == "":
                continue

            queryset = self.filter_by_attribute(queryset, key, value)

        sort = self.request.query_params.get("sort")

        if sort == "newest":
            return queryset.order_by("-created_at").distinct()

        if sort == "oldest":
            return queryset.order_by("created_at").distinct()

        if sort == "price_low":
            return queryset.order_by("price").distinct()

        if sort == "price_high":
            return queryset.order_by("-price").distinct()

        if sort == "popular":
            return queryset.order_by("-views_count", "-created_at").distinct()

        return queryset.order_by("-created_at").distinct()

    def filter_by_attribute(self, queryset, key, value):
        value_text = str(value).strip()
        value_lower = value_text.lower()

        # Boolean filters: furnished=true / furnished=false
        if value_lower in ["true", "false"]:
            return queryset.filter(
                attributes__category_filter__key=key,
                attributes__value_boolean=(value_lower == "true"),
            )

        # Number filters: year=2012 / bedrooms=2 / mileage=85000
        try:
            number_value = Decimal(value_text)

            number_queryset = queryset.filter(
                attributes__category_filter__key=key,
                attributes__value_number=number_value,
            )

            if number_queryset.exists():
                return number_queryset

        except (InvalidOperation, ValueError):
            pass

        # Text/select filters: brand=Toyota / storage=256GB / ram=16GB
        return queryset.filter(
            attributes__category_filter__key=key,
            attributes__value_text__iexact=value_text,
        )


class PendingListingImageAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBanned,
        IsVerifiedUser,
    ]

    def post(self, request):
        expired_images = PendingListingImage.objects.filter(
            user=request.user,
            created_at__lt=timezone.now() - timedelta(hours=24),
        )

        for expired_image in expired_images:
            expired_image.image.delete(save=False)
            expired_image.delete()

        image_serializer = ListingImageSerializer(data=request.data)
        image_serializer.is_valid(raise_exception=True)

        pending_count = PendingListingImage.objects.filter(user=request.user).count()

        if pending_count >= 10:
            return Response(
                {"detail": "You can stage a maximum of 10 photos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pending_image = PendingListingImage.objects.create(
            user=request.user,
            image=image_serializer.validated_data["image"],
        )

        return Response(
            {
                "id": pending_image.id,
                "image_url": request.build_absolute_uri(pending_image.image.url),
            },
            status=status.HTTP_201_CREATED,
        )

    def delete(self, request, pk):
        pending_image = PendingListingImage.objects.filter(
            pk=pk,
            user=request.user,
        ).first()

        if not pending_image:
            return Response(
                {"detail": "Staged photo not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        pending_image.image.delete(save=False)
        pending_image.delete()
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
            .prefetch_related("images", "attributes", "attributes__category_filter")
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

        is_first_image = current_images_count == 0

        image = serializer.save(
            listing=listing,
            is_primary=is_first_image,
        )

        response_serializer = ListingImageSerializer(
            image,
            context={"request": request},
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
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

        image.image.delete(save=False)
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
