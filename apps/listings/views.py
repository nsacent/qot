from django.db.models import F,Q
from django.utils.text import slugify
from .filters import ListingFilter

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Listing, ListingImage
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
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        listing = serializer.save()

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
        return (
            Listing.objects
            .select_related("seller", "category", "city")
            .prefetch_related("images", "attributes", "attributes__category_filter")
            .exclude(status=Listing.STATUS_DELETED)
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.status == Listing.STATUS_ACTIVE:
            Listing.objects.filter(pk=instance.pk).update(
                views_count=F("views_count") + 1
            )
            instance.refresh_from_db(fields=["views_count"])

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_destroy(self, instance):
        instance.soft_delete()


    def retrieve(self, request, *args, **kwargs):
        listing = self.get_object()

        if request.method == "GET":
            Listing.objects.filter(pk=listing.pk).update(
                views_count=listing.views_count + 1
            )

            listing.refresh_from_db(fields=["views_count"])

        serializer = self.get_serializer(listing)

        return Response(serializer.data)


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

        if listing.status == Listing.STATUS_DELETED:
            return Response(
                {"detail": "Deleted listings cannot be marked as sold."},
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

        if listing.status == Listing.STATUS_DELETED:
            return Response(
                {"detail": "Deleted listings cannot be made available."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if listing.status == Listing.STATUS_REJECTED:
            return Response(
                {"detail": "Rejected listings must be edited and resubmitted."},
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

        if listing.status == Listing.STATUS_DELETED:
            return Response(
                {"detail": "Deleted listings cannot be relisted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if listing.status == Listing.STATUS_REJECTED:
            return Response(
                {"detail": "Rejected listings must be edited and resubmitted."},
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

        if listing.status == Listing.STATUS_DELETED:
            return Response(
                {"detail": "Deleted listings cannot be renewed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if listing.status == Listing.STATUS_REJECTED:
            return Response(
                {"detail": "Rejected listings must be edited and resubmitted for approval."},
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