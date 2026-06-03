from django.urls import path

from .views import (
    CategoryListAPIView,
    CategoryDetailAPIView,
    CategoryFilterListAPIView,
)


app_name = "categories"


urlpatterns = [
    path("", CategoryListAPIView.as_view(), name="category_list"),
    path("<slug:slug>/", CategoryDetailAPIView.as_view(), name="category_detail"),
    path("<slug:slug>/filters/", CategoryFilterListAPIView.as_view(), name="category_filters"),
]