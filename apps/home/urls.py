from django.urls import path

from .views import HomeAPIView


app_name = "home"


urlpatterns = [
    path("", HomeAPIView.as_view(), name="home"),
]