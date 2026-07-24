from django.core.management import call_command
from django.test import TestCase

from .catalog import FILTER_SPECS_BY_SLUG
from .models import Category, CategoryFilter, CategoryFilterOption


class CategoryFilterCatalogTests(TestCase):
    def setUp(self):
        vehicles = Category.objects.create(name="Vehicles", slug="vehicles")
        electronics = Category.objects.create(name="Electronics", slug="electronics")
        self.cars = Category.objects.create(name="Cars", slug="cars", parent=vehicles)
        self.cameras = Category.objects.create(
            name="Cameras", slug="cameras", parent=electronics
        )
        self.vehicle_services = Category.objects.create(
            name="Vehicle Services", slug="vehicle-services", parent=vehicles
        )
        self.wrong_filter = CategoryFilter.objects.create(
            category=self.vehicle_services,
            name="Mileage",
            key="mileage",
            filter_type=CategoryFilter.TYPE_NUMBER,
        )
        CategoryFilterOption.objects.create(
            category_filter=self.wrong_filter,
            label="Wrong option",
            value="Wrong option",
        )

    def test_command_applies_exact_relevant_specs(self):
        call_command("seed_category_filters")

        cars = self.cars.filters.filter(is_searchable=True).order_by("sort_order")
        cameras = self.cameras.filters.filter(is_searchable=True).order_by("sort_order")
        vehicle_services = self.vehicle_services.filters.filter(
            is_searchable=True
        ).order_by("sort_order")

        self.assertEqual(
            list(cars.values_list("key", flat=True)),
            [spec["key"] for spec in FILTER_SPECS_BY_SLUG["cars"]],
        )
        self.assertEqual(
            list(cameras.values_list("key", flat=True)),
            ["brand", "camera_type", "megapixels", "lens_mount"],
        )
        self.assertEqual(
            list(vehicle_services.values_list("key", flat=True)),
            ["service_type", "vehicle_type", "service_location"],
        )
        self.wrong_filter.refresh_from_db()
        self.assertFalse(self.wrong_filter.is_searchable)
        self.assertLessEqual(cars.count(), 6)

    def test_command_populates_options_and_is_idempotent(self):
        call_command("seed_category_filters")
        call_command("seed_category_filters")

        transmission = self.cars.filters.get(key="transmission")
        self.assertEqual(
            list(
                transmission.options.filter(is_active=True)
                .order_by("sort_order")
                .values_list("value", flat=True)
            ),
            ["Automatic", "Manual"],
        )
        self.assertEqual(
            self.cars.filters.filter(key="transmission").count(),
            1,
        )

    def test_category_api_hides_obsolete_filters_and_options(self):
        call_command("seed_category_filters")
        service_type = self.vehicle_services.filters.get(key="service_type")
        CategoryFilterOption.objects.create(
            category_filter=service_type,
            label="Obsolete",
            value="Obsolete",
            is_active=False,
        )

        response = self.client.get("/api/v1/categories/vehicle-services/")

        self.assertEqual(response.status_code, 200)
        keys = [item["key"] for item in response.data["filters"]]
        option_values = [
            option["value"]
            for item in response.data["filters"]
            for option in item["options"]
        ]
        self.assertNotIn("mileage", keys)
        self.assertNotIn("Obsolete", option_values)

    def test_category_api_includes_photo_requirements(self):
        response = self.client.get("/api/v1/categories/")

        self.assertEqual(response.status_code, 200)
        vehicles = next(item for item in response.data if item["slug"] == "vehicles")
        cars = next(item for item in vehicles["children"] if item["slug"] == "cars")
        vehicle_services = next(
            item for item in vehicles["children"] if item["slug"] == "vehicle-services"
        )

        self.assertEqual(cars["minimum_photos"], 4)
        self.assertEqual(cars["maximum_photos"], 10)
        self.assertEqual(vehicle_services["minimum_photos"], 1)
        self.assertEqual(vehicle_services["maximum_photos"], 5)
