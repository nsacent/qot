from django.urls import path

from .views import (
    PaymentCreateAPIView,
    MyPaymentListAPIView,
    PromotionPackageListAPIView,
)

app_name = "payments"


urlpatterns = [
    path("", PaymentCreateAPIView.as_view(), name="create_payment"),
    path("me/", MyPaymentListAPIView.as_view(), name="my_payments"),
    path("packages/", PromotionPackageListAPIView.as_view(), name="packages"),
]