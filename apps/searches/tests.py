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

    def test_saved_search_alerts_can_be_enabled_and_disabled(self):
        saved_search = SavedSearch.objects.create(
            user=self.user,
            name="Kampala laptops",
            query="laptop",
            filters={"city": "kampala"},
            notify_user=True,
        )

        response = self.client.patch(
            f"/api/v1/searches/saved/{saved_search.id}/",
            {"notify_user": False},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["notify_user"])
        saved_search.refresh_from_db()
        self.assertFalse(saved_search.notify_user)

    def test_user_cannot_update_another_users_saved_search(self):
        other_user = User.objects.create_user(
            phone="+256700009002",
            email="other-saved-search@example.com",
            full_name="Other Saved Search User",
            password="test-password",
            is_verified=True,
        )
        saved_search = SavedSearch.objects.create(
            user=other_user,
            name="Private search",
            query="phone",
            filters={},
            notify_user=True,
        )

        response = self.client.patch(
            f"/api/v1/searches/saved/{saved_search.id}/",
            {"notify_user": False},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
