from django.urls import path

from .views import (
    RecentSearchListCreateAPIView,
    ClearRecentSearchesAPIView,
    SavedSearchListCreateAPIView,
    SavedSearchDetailAPIView,
)


app_name = "searches"


urlpatterns = [
    path(
        "recent/",
        RecentSearchListCreateAPIView.as_view(),
        name="recent_searches",
    ),
    path(
        "recent/clear/",
        ClearRecentSearchesAPIView.as_view(),
        name="clear_recent_searches",
    ),
    path(
        "saved/",
        SavedSearchListCreateAPIView.as_view(),
        name="saved_searches",
    ),
    path(
        "saved/<int:pk>/",
        SavedSearchDetailAPIView.as_view(),
        name="saved_search_detail",
    ),
]
