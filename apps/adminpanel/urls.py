from django.urls import path

from .views import (
    AdminDashboardAPIView,
    AdminListingListAPIView,
    PendingListingListAPIView,
    ApproveListingAPIView,
    RejectListingAPIView,
    FeatureListingAPIView,
    UnfeatureListingAPIView,
    AdminUserListAPIView,
    BanUserAPIView,
    UnbanUserAPIView,
    AdminPaymentListAPIView,
    AdminMarkPaymentPaidAPIView,
    AdminMarkPaymentFailedAPIView,
    AdminPromotionPackageListCreateAPIView,
    AdminPromotionPackageDetailAPIView,
)


app_name = "adminpanel"


urlpatterns = [
    path("dashboard/", AdminDashboardAPIView.as_view(), name="dashboard"),

    path("listings/", AdminListingListAPIView.as_view(), name="listing_list"),
    path("listings/pending/", PendingListingListAPIView.as_view(), name="pending_listing_list"),
    path("listings/<int:pk>/approve/", ApproveListingAPIView.as_view(), name="approve_listing"),
    path("listings/<int:pk>/reject/", RejectListingAPIView.as_view(), name="reject_listing"),

    path("listings/<int:pk>/feature/", FeatureListingAPIView.as_view(), name="feature_listing"),
    path("listings/<int:pk>/unfeature/", UnfeatureListingAPIView.as_view(), name="unfeature_listing"),

    path("users/", AdminUserListAPIView.as_view(), name="user_list"),
    path("users/<int:pk>/ban/", BanUserAPIView.as_view(), name="ban_user"),
    path("users/<int:pk>/unban/", UnbanUserAPIView.as_view(), name="unban_user"),
    
    
    path("payments/", AdminPaymentListAPIView.as_view(), name="payment_list"),
    path("payments/<int:pk>/mark-paid/", AdminMarkPaymentPaidAPIView.as_view(), name="payment_mark_paid"),
    path("payments/<int:pk>/mark-failed/", AdminMarkPaymentFailedAPIView.as_view(), name="payment_mark_failed"),

    path("packages/", AdminPromotionPackageListCreateAPIView.as_view(), name="package_list_create"),
    path("packages/<int:pk>/", AdminPromotionPackageDetailAPIView.as_view(), name="package_detail"),
]