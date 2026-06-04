from django.db.models import F
from django.utils.text import slugify
from .filters import ListingFilter

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Listing, ListingImage
from .permissions import IsListingOwnerOrReadOnly

from .serializers import (
    ListingListSerializer,
    ListingDetailSerializer,
    ListingCreateUpdateSerializer,
    ListingImageSerializer,

)

from apps.common.permissions import IsNotBanned

from datetime import timedelta
from django.utils import timezone


class ListingListCreateAPIView(generics.ListCreateAPIView):
    filterset_class = ListingFilter

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated(), IsNotBanned()]

        return [permissions.AllowAny()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ListingCreateUpdateSerializer

        return ListingListSerializer

    def get_queryset(self):
        queryset = (
            Listing.objects
            .select_related("seller", "category", "city")
            .prefetch_related("images")
            .exclude(status=Listing.STATUS_DELETED)
        )

        if self.request.user.is_authenticated:
            if self.request.query_params.get("mine") == "true":
                return queryset.filter(seller=self.request.user)

        return queryset.filter(status=Listing.STATUS_ACTIVE)

    def perform_create(self, serializer):
        listing = serializer.save()

        base_slug = slugify(listing.title)
        listing.slug = f"{base_slug}-{listing.id}"
        listing.save(update_fields=["slug"])
        

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)

        sort = self.request.query_params.get("sort")

        if sort == "newest":
            return queryset.order_by("-created_at")

        if sort == "oldest":
            return queryset.order_by("created_at")

        if sort == "price_low":
            return queryset.order_by("price")

        if sort == "price_high":
            return queryset.order_by("-price")

        if sort == "popular":
            return queryset.order_by("-views_count", "-created_at")

        return queryset.order_by("-created_at")


class ListingDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]

        return [
            permissions.IsAuthenticated(),
            IsNotBanned(),
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


class MarkListingSoldAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBanned,
    ]

    def post(self, request, pk):
        try:
            listing = Listing.objects.get(pk=pk, seller=request.user)
        except Listing.DoesNotExist:
            return Response(
                {
                    "detail": "Listing not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if listing.status == Listing.STATUS_SOLD:
            return Response(
                {
                    "detail": "Listing is already marked as sold."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        listing.mark_sold()

        return Response(
            {
                "message": "Listing marked as sold successfully."
            },
            status=status.HTTP_200_OK,
        )


class RenewListingAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBanned,
    ]

    def post(self, request, pk):
        try:
            listing = Listing.objects.get(pk=pk, seller=request.user)
        except Listing.DoesNotExist:
            return Response(
                {"detail": "Listing not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if listing.status not in [
            Listing.STATUS_ACTIVE,
            Listing.STATUS_EXPIRED,
        ]:
            return Response(
                {
                    "detail": "Only active or expired listings can be renewed."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        listing.status = Listing.STATUS_ACTIVE
        listing.expires_at = timezone.now() + timedelta(days=30)
        listing.save(update_fields=["status", "expires_at", "updated_at"])

        return Response(
            {
                "message": "Listing renewed successfully.",
                "expires_at": listing.expires_at,
            },
            status=status.HTTP_200_OK,
        )


class ListingImageUploadAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBanned,
    ]

    def post(self, request, pk):
        try:
            listing = Listing.objects.get(
                pk=pk,
                seller=request.user,
            )
        except Listing.DoesNotExist:
            return Response(
                {
                    "detail": "Listing not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        image_count = listing.images.count()

        if image_count >= 10:
            return Response(
                {
                    "detail": "A listing cannot have more than 10 images."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ListingImageSerializer(data=request.data)

        if serializer.is_valid():
            image = serializer.save(
                listing=listing,
                sort_order=image_count,
            )

            if listing.images.count() == 1:
                image.is_primary = True
                image.save(update_fields=["is_primary"])

            return Response(
                ListingImageSerializer(image, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ListingImageDeleteAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBanned,
    ]

    def delete(self, request, pk, image_id):
        try:
            image = ListingImage.objects.select_related("listing").get(
                pk=image_id,
                listing_id=pk,
                listing__seller=request.user,
            )
        except ListingImage.DoesNotExist:
            return Response(
                {
                    "detail": "Image not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        was_primary = image.is_primary
        listing = image.listing

        image.delete()

        if was_primary:
            next_image = listing.images.order_by("sort_order", "id").first()

            if next_image:
                next_image.is_primary = True
                next_image.save(update_fields=["is_primary"])

        return Response(
            {
                "message": "Image deleted successfully."
            },
            status=status.HTTP_200_OK,
        )