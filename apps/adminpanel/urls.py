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
    AdminUserDetailAPIView,
    BanUserAPIView,
    UnbanUserAPIView,
    AdminPaymentListAPIView,
    AdminMarkPaymentPaidAPIView,
    AdminMarkPaymentFailedAPIView,
    AdminPromotionPackageListCreateAPIView,
    AdminPromotionPackageDetailAPIView,
    AdminCancelPaymentAPIView,
    AdminSellerReviewListAPIView,
    AdminHideSellerReviewAPIView,
    AdminShowSellerReviewAPIView,
    AdminChatReportListAPIView,
    AdminChatReportDetailAPIView,
    ResolveChatReportAPIView,
    AdminChatBlockListAPIView,
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
    path("users/<int:pk>/", AdminUserDetailAPIView.as_view(), name="user_detail"),
    path("users/<int:pk>/ban/", BanUserAPIView.as_view(), name="ban_user"),
    path("users/<int:pk>/unban/", UnbanUserAPIView.as_view(), name="unban_user"),
    
    
    path("payments/", AdminPaymentListAPIView.as_view(), name="payment_list"),
    path("payments/<int:pk>/mark-paid/", AdminMarkPaymentPaidAPIView.as_view(), name="payment_mark_paid"),
    path("payments/<int:pk>/mark-failed/", AdminMarkPaymentFailedAPIView.as_view(), name="payment_mark_failed"),

    path("packages/", AdminPromotionPackageListCreateAPIView.as_view(), name="package_list_create"),
    path("packages/<int:pk>/", AdminPromotionPackageDetailAPIView.as_view(), name="package_detail"),

    path("payments/<int:pk>/cancel/", AdminCancelPaymentAPIView.as_view(), name="payment_cancel"),

    path("reviews/", AdminSellerReviewListAPIView.as_view(), name="review_list"),
    path("reviews/<int:pk>/hide/", AdminHideSellerReviewAPIView.as_view(), name="review_hide"),
    path("reviews/<int:pk>/show/", AdminShowSellerReviewAPIView.as_view(), name="review_show"),

    path("chat-reports/", AdminChatReportListAPIView.as_view(), name="chat_report_list"),
    path("chat-reports/<int:pk>/", AdminChatReportDetailAPIView.as_view(), name="chat_report_detail"),
    path("chat-reports/<int:pk>/resolve/", ResolveChatReportAPIView.as_view(), name="chat_report_resolve"),
    path("chat-blocks/", AdminChatBlockListAPIView.as_view(), name="chat_block_list"),
]
