from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User

from .models import SavedSearch


class SavedSearchAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone="+256700009001",
            email="saved-search@example.com",
            full_name="Saved Search User",
            password="test-password",
            is_verified=True,
        )
        self.client.force_authenticate(self.user)

    def test_saved_search_is_created_for_authenticated_user(self):
        response = self.client.post(
            "/api/v1/searches/saved/",
            {
                "name": "Category: vehicles · City: Kampala",
                "query": "",
                "filters": {"category": "vehicles", "city": "kampala"},
                "notify_user": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        saved_search = SavedSearch.objects.get(user=self.user)
        self.assertEqual(saved_search.filters["city"], "kampala")

    def test_duplicate_saved_search_returns_friendly_validation_error(self):
        payload = {
            "name": "Search: laptop",
            "query": "laptop",
            "filters": {},
            "notify_user": False,
        }
        first_response = self.client.post(
            "/api/v1/searches/saved/",
            payload,
            format="json",
        )
        duplicate_response = self.client.post(
            "/api/v1/searches/saved/",
            payload,
            format="json",
        )

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(duplicate_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already saved", str(duplicate_response.data))
        self.assertEqual(SavedSearch.objects.filter(user=self.user).count(), 1)
