from rest_framework import status
from rest_framework.test import APITestCase

from .models import Area, City, Region


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

    def test_area_catalog_can_be_filtered_by_city(self):
        central = Region.objects.create(name="Central", slug="central")
        kampala = City.objects.create(
            region=central,
            name="Kampala",
            slug="kampala",
        )
        wakiso = City.objects.create(
            region=central,
            name="Wakiso",
            slug="wakiso",
        )
        Area.objects.create(city=kampala, name="Kawempe", slug="kawempe")
        Area.objects.create(city=kampala, name="Makindye", slug="makindye")
        Area.objects.create(city=wakiso, name="Kira", slug="kira")

        response = self.client.get("/api/v1/locations/areas/?city=kampala")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [area["name"] for area in response.data],
            ["Kawempe", "Makindye"],
        )
        self.assertTrue(all(area["city_name"] == "Kampala" for area in response.data))

    def test_city_catalog_includes_only_active_areas(self):
        central = Region.objects.create(name="Central", slug="central")
        kampala = City.objects.create(
            region=central,
            name="Kampala",
            slug="kampala",
        )
        Area.objects.create(city=kampala, name="Nakawa", slug="nakawa")
        Area.objects.create(
            city=kampala,
            name="Retired area",
            slug="retired-area",
            is_active=False,
        )

        response = self.client.get("/api/v1/locations/cities/?region=central")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [area["name"] for area in response.data[0]["areas"]],
            ["Nakawa"],
        )
