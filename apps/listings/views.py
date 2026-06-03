from django.db.models import F
from django.utils.text import slugify

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Listing
from .permissions import IsListingOwnerOrReadOnly, IsNotBanned
from .serializers import (
    ListingListSerializer,
    ListingDetailSerializer,
    ListingCreateUpdateSerializer,
)


class ListingListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

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


class ListingDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        IsListingOwnerOrReadOnly,
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