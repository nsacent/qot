from django.apps import AppConfig
from pillow_heif import register_heif_opener


class ListingsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.listings"
    label = "listings"

    def ready(self):
        register_heif_opener()
