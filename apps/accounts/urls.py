from django.urls import path

from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    RegisterAPIView,
    LoginAPIView,
    LogoutAPIView,
    MeAPIView,
    PasswordResetRequestAPIView,
    PasswordResetConfirmAPIView,
    SendVerificationCodeAPIView,
    ConfirmVerificationCodeAPIView,
)

app_name = "accounts"


urlpatterns = [
    path("register/", RegisterAPIView.as_view(), name="register"),
    path("login/", LoginAPIView.as_view(), name="login"),
    path("logout/", LogoutAPIView.as_view(), name="logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
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