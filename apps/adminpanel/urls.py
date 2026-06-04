from django.urls import path

from .views import (
    AdminDashboardAPIView,
    AdminListingListAPIView,
    PendingListingListAPIView,
    ApproveListingAPIView,
    RejectListingAPIView,
    AdminUserListAPIView,
    BanUserAPIView,
    UnbanUserAPIView,
)


app_name = "adminpanel"


urlpatterns = [
    path("dashboard/", AdminDashboardAPIView.as_view(), name="dashboard"),

    path("listings/", AdminListingListAPIView.as_view(), name="listing_list"),
    path("listings/pending/", PendingListingListAPIView.as_view(), name="pending_listing_list"),
    path("listings/<int:pk>/approve/", ApproveListingAPIView.as_view(), name="approve_listing"),
    path("listings/<int:pk>/reject/", RejectListingAPIView.as_view(), name="reject_listing"),

    path("users/", AdminUserListAPIView.as_view(), name="user_list"),
    path("users/<int:pk>/ban/", BanUserAPIView.as_view(), name="ban_user"),
    path("users/<int:pk>/unban/", UnbanUserAPIView.as_view(), name="unban_user"),
]