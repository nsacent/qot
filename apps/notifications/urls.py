from django.urls import path

from .views import (
    NotificationListAPIView,
    NotificationMarkReadAPIView,
    NotificationMarkAllReadAPIView,
)


app_name = "notifications"


urlpatterns = [
    path("", NotificationListAPIView.as_view(), name="notification_list"),
    path("<int:pk>/read/", NotificationMarkReadAPIView.as_view(), name="notification_read"),
    path("read-all/", NotificationMarkAllReadAPIView.as_view(), name="notification_read_all"),
]