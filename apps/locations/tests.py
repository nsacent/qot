from rest_framework import status
from rest_framework.test import APITestCase

from .models import City, Region


class LocationCatalogTests(APITestCase):
    def test_city_catalog_is_not_truncated_by_global_pagination(self):
        central = Region.objects.create(name="Central", slug="central")
        eastern = Region.objects.create(name="Eastern", slug="eastern")

        for index in range(65):
            region = central if index < 40 else eastern
            City.objects.create(
                region=region,
                name=f"Catalog City {index:02d}",
                slug=f"catalog-city-{index:02d}",
            )

        response = self.client.get("/api/v1/locations/cities/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 65)
        self.assertEqual(
            sum(city["region_name"] == "Central" for city in response.data),
            40,
        )

    def test_region_catalog_is_not_paginated(self):
        for index in range(55):
            Region.objects.create(
                name=f"Region {index:02d}",
                slug=f"region-{index:02d}",
            )

        response = self.client.get("/api/v1/locations/regions/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 55)
