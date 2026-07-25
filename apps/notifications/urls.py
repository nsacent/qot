from django.urls import path

from .views import (
    NotificationListAPIView,
    NotificationMarkReadAPIView,
    NotificationMarkAllReadAPIView,
    PushDeviceAPIView,
)


app_name = "notifications"


urlpatterns = [
    path("", NotificationListAPIView.as_view(), name="notification_list"),
    path("<int:pk>/read/", NotificationMarkReadAPIView.as_view(), name="notification_read"),
    path("read-all/", NotificationMarkAllReadAPIView.as_view(), name="notification_read_all"),
    path("devices/", PushDeviceAPIView.as_view(), name="push_device"),
]
