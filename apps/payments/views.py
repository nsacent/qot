from rest_framework import generics, permissions

from apps.common.permissions import IsNotBanned, IsVerifiedUser

from .models import Payment, PromotionPackage
from .serializers import (
    PaymentSerializer,
    PaymentCreateSerializer,
    PromotionPackageSerializer,
)


class PaymentCreateAPIView(generics.CreateAPIView):
    serializer_class = PaymentCreateSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBanned,
        IsVerifiedUser,
    ]


class MyPaymentListAPIView(generics.ListAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get_queryset(self):
        return (
            Payment.objects
            .filter(user=self.request.user)
            .select_related("listing")
            .order_by("-created_at")
        )

class PromotionPackageListAPIView(generics.ListAPIView):
    serializer_class = PromotionPackageSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = PromotionPackage.objects.filter(is_active=True)

        package_type = self.request.query_params.get("package_type")

        if package_type:
            queryset = queryset.filter(package_type=package_type)

        return queryset.order_by("sort_order", "price", "name")