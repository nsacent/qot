from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsNotBanned

from .models import RecentSearch, SavedSearch
from .serializers import RecentSearchSerializer, SavedSearchSerializer


class RecentSearchListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = RecentSearchSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBanned,
    ]

    def get_queryset(self):
        return RecentSearch.objects.filter(
            user=self.request.user,
        ).order_by("-created_at")[:20]

    def perform_create(self, serializer):
        query = serializer.validated_data.get("query", "")
        filters = serializer.validated_data.get("filters", {})

        RecentSearch.objects.filter(
            user=self.request.user,
            query=query,
            filters=filters,
        ).delete()

        serializer.save(user=self.request.user)

        old_searches = RecentSearch.objects.filter(
            user=self.request.user,
        ).order_by("-created_at")[20:]

        RecentSearch.objects.filter(
            id__in=[search.id for search in old_searches]
        ).delete()


class ClearRecentSearchesAPIView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBanned,
    ]

    def delete(self, request):
        RecentSearch.objects.filter(user=request.user).delete()

        return Response(
            {"message": "Recent searches cleared successfully."},
            status=status.HTTP_200_OK,
        )


class SavedSearchListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = SavedSearchSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBanned,
    ]

    def get_queryset(self):
        return SavedSearch.objects.filter(
            user=self.request.user,
        ).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SavedSearchDeleteAPIView(generics.DestroyAPIView):
    serializer_class = SavedSearchSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsNotBanned,
    ]

    def get_queryset(self):
        return SavedSearch.objects.filter(user=self.request.user)