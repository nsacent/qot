from django.apps import AppConfig
from pillow_heif import register_heif_opener


class ListingsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.listings"
    label = "listings"

    def ready(self):
        # Uploads use the primary photo, not portrait depth maps or HDR auxiliaries.
        register_heif_opener(thumbnails=False, depth_images=False, aux_images=False)
