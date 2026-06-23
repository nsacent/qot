from django.urls import path

from .views import MyCountsAPIView


app_name = "me"


urlpatterns = [
    path("counts/", MyCountsAPIView.as_view(), name="counts"),
]