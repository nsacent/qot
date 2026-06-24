from django.db.models import Count, Q
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.categories.models import Category
from apps.listings.models import Listing
from django.utils import timezone

from .serializers import HomeListingSerializer, HomeCategorySerializer


class HomeAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get_base_queryset(self):
        return (
            Listing.objects
            .filter(status=Listing.STATUS_ACTIVE)
            .select_related("seller", "category", "category__parent", "city", "city__region")
            .prefetch_related("images")
        )

    def get(self, request):
        listings = self.get_base_queryset()

        featured_listings = listings.filter(
            is_featured=True,
            featured_until__gt=timezone.now(),
        ).order_by("-created_at")[:10]

        latest_listings = listings.order_by("-created_at")[:10]

        popular_listings = listings.order_by("-views_count", "-favorites_count", "-created_at")[:10]

        recent_cars = listings.filter(
            Q(category__slug="cars") | Q(category__parent__slug="vehicles")
        ).order_by("-created_at")[:10]

        recent_phones = listings.filter(
            Q(category__slug="phones") | Q(category__parent__slug="phones-tablets")
        ).order_by("-created_at")[:10]

        recent_laptops = listings.filter(
            Q(category__slug="laptops") | Q(category__parent__slug="electronics")
        ).order_by("-created_at")[:10]

        popular_categories = (
            Category.objects
            .filter(is_active=True, parent__isnull=True)
            .annotate(
                listings_count=Count(
                    "children__listings",
                    filter=Q(children__listings__status=Listing.STATUS_ACTIVE),
                )
            )
            .order_by("-listings_count", "sort_order", "name")[:10]
        )

        context = {"request": request}

        data = {
            "featured_listings": HomeListingSerializer(
                featured_listings,
                many=True,
                context=context,
            ).data,
            "latest_listings": HomeListingSerializer(
                latest_listings,
                many=True,
                context=context,
            ).data,
            "popular_listings": HomeListingSerializer(
                popular_listings,
                many=True,
                context=context,
            ).data,
            "popular_categories": HomeCategorySerializer(
                popular_categories,
                many=True,
                context=context,
            ).data,
            "recent_cars": HomeListingSerializer(
                recent_cars,
                many=True,
                context=context,
            ).data,
            "recent_phones": HomeListingSerializer(
                recent_phones,
                many=True,
                context=context,
            ).data,
            "recent_laptops": HomeListingSerializer(
                recent_laptops,
                many=True,
                context=context,
            ).data,
        }

        return Response(data, status=status.HTTP_200_OK)