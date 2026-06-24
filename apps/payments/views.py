from rest_framework import generics, permissions

from apps.common.permissions import IsNotBanned, IsVerifiedUser

from .models import Payment
from .serializers import PaymentSerializer, PaymentCreateSerializer


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