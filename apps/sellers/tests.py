from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserFollow
from apps.categories.models import Category
from apps.listings.models import Listing
from apps.locations.models import City, Region
from apps.reviews.models import SellerReview


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

    def test_public_seller_directory_only_shows_sellers_with_active_ads(self):
        region = Region.objects.create(name="Central Test", slug="central-test")
        city = City.objects.create(
            region=region,
            name="Kampala Test",
            slug="kampala-test",
        )
        category = Category.objects.create(
            name="Directory Test",
            slug="directory-test",
        )
        leading_listing = Listing.objects.create(
            seller=self.seller,
            category=category,
            city=city,
            title="Active seller advert",
            slug="active-seller-advert",
            description="Seller directory test advert.",
            price="100000.00",
            status=Listing.STATUS_ACTIVE,
            views_count=120,
        )
        SellerReview.objects.create(
            reviewer=self.follower,
            seller=self.seller,
            listing=leading_listing,
            rating=4,
        )

        second_seller = User.objects.create_user(
            phone="+256700009003",
            email="second-seller@example.com",
            full_name="Second Seller",
            password="test-password",
            is_verified=True,
        )
        second_listing = Listing.objects.create(
            seller=second_seller,
            category=category,
            city=city,
            title="Lower viewed advert",
            slug="lower-viewed-advert",
            description="A qualifying seller with fewer advert views.",
            price="90000.00",
            status=Listing.STATUS_ACTIVE,
            views_count=25,
        )
        SellerReview.objects.create(
            reviewer=self.follower,
            seller=second_seller,
            listing=second_listing,
            rating=5,
        )

        low_rated_seller = User.objects.create_user(
            phone="+256700009004",
            email="low-rated@example.com",
            full_name="Low Rated Seller",
            password="test-password",
            is_verified=True,
        )
        low_rated_listing = Listing.objects.create(
            seller=low_rated_seller,
            category=category,
            city=city,
            title="Low rated advert",
            slug="low-rated-advert",
            description="This seller should not appear because of rating.",
            price="80000.00",
            status=Listing.STATUS_ACTIVE,
            views_count=500,
        )
        SellerReview.objects.create(
            reviewer=self.follower,
            seller=low_rated_seller,
            listing=low_rated_listing,
            rating=3,
        )

        unverified_seller = User.objects.create_user(
            phone="+256700009005",
            email="unverified-directory@example.com",
            full_name="Unverified Seller",
            password="test-password",
            is_verified=False,
        )
        unverified_listing = Listing.objects.create(
            seller=unverified_seller,
            category=category,
            city=city,
            title="Unverified advert",
            slug="unverified-directory-advert",
            description="This seller should not appear because verification is missing.",
            price="70000.00",
            status=Listing.STATUS_ACTIVE,
            views_count=900,
        )
        SellerReview.objects.create(
            reviewer=self.follower,
            seller=unverified_seller,
            listing=unverified_listing,
            rating=5,
        )
        Listing.objects.create(
            seller=self.follower,
            category=category,
            city=city,
            title="Draft seller advert",
            slug="draft-seller-advert",
            description="This seller should not appear.",
            price="120000.00",
            status=Listing.STATUS_DRAFT,
        )

        response = self.client.get("/api/v1/sellers/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data["results"][0]["id"], self.seller.id)
        self.assertEqual(response.data["results"][1]["id"], second_seller.id)
        self.assertEqual(
            response.data["results"][0]["total_active_listings"],
            1,
        )

        search_response = self.client.get("/api/v1/sellers/?search=Seller")
        self.assertEqual(search_response.data["count"], 2)
