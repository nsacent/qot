from django.urls import path

from rest_framework_simplejwt.views import TokenRefreshView

from .serializers import QOTTokenRefreshSerializer

from .views import (
    RegisterAPIView,
    LoginAPIView,
    GoogleLoginAPIView,
    LogoutAPIView,
    MeAPIView,
    PasswordResetRequestAPIView,
    PasswordResetConfirmAPIView,
    SendVerificationCodeAPIView,
    ConfirmVerificationCodeAPIView,
)

app_name = "accounts"


class QOTTokenRefreshView(TokenRefreshView):
    serializer_class = QOTTokenRefreshSerializer


urlpatterns = [
    path("register/", RegisterAPIView.as_view(), name="register"),
    path("login/", LoginAPIView.as_view(), name="login"),
    path("google/", GoogleLoginAPIView.as_view(), name="google_login"),
    path("logout/", LogoutAPIView.as_view(), name="logout"),
    path("token/refresh/", QOTTokenRefreshView.as_view(), name="token_refresh"),
    path("me/", MeAPIView.as_view(), name="me"),

    path(
        "password-reset/request/",
        PasswordResetRequestAPIView.as_view(),
        name="password_reset_request",
    ),
    path(
        "password-reset/confirm/",
        PasswordResetConfirmAPIView.as_view(),
        name="password_reset_confirm",
    ),

    path(
        "verification/send/",
        SendVerificationCodeAPIView.as_view(),
        name="verification_send",
    ),
    path(
        "verification/confirm/",
        ConfirmVerificationCodeAPIView.as_view(),
        name="verification_confirm",
    ),
]
