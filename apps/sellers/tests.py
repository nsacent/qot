from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserFollow


class SellerFollowTests(APITestCase):
    def setUp(self):
        self.follower = User.objects.create_user(
            phone="+256700009001",
            email="follower@example.com",
            full_name="Follower",
            password="test-password",
            is_verified=True,
        )
        self.seller = User.objects.create_user(
            phone="+256700009002",
            email="seller@example.com",
            full_name="Seller",
            password="test-password",
            is_verified=True,
        )
        self.client.force_authenticate(self.follower)

    def test_follow_is_idempotent_and_visible_on_profile(self):
        url = f"/api/v1/sellers/{self.seller.id}/follow/"

        first_response = self.client.post(url, {}, format="json")
        second_response = self.client.post(url, {}, format="json")

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            UserFollow.objects.filter(
                follower=self.follower,
                following=self.seller,
            ).count(),
            1,
        )

        profile_response = self.client.get(f"/api/v1/sellers/{self.seller.id}/")
        self.assertTrue(profile_response.data["is_following"])
        self.assertEqual(profile_response.data["followers_count"], 1)

    def test_user_cannot_follow_self(self):
        response = self.client.post(
            f"/api/v1/sellers/{self.follower.id}/follow/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(UserFollow.objects.exists())

    def test_unfollow_and_follow_lists(self):
        UserFollow.objects.create(follower=self.follower, following=self.seller)

        followers_response = self.client.get(
            f"/api/v1/sellers/{self.seller.id}/followers/"
        )
        following_response = self.client.get(
            f"/api/v1/sellers/{self.follower.id}/following/"
        )

        self.assertEqual(followers_response.data["results"][0]["id"], self.follower.id)
        self.assertEqual(following_response.data["results"][0]["id"], self.seller.id)

        delete_response = self.client.delete(
            f"/api/v1/sellers/{self.seller.id}/follow/"
        )
        self.assertEqual(delete_response.status_code, status.HTTP_200_OK)
        self.assertFalse(UserFollow.objects.exists())
