from django.contrib import admin

from .models import Favorite


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "listing",
        "created_at",
    ]

    list_filter = [
        "created_at",
    ]

    search_fields = [
        "user__phone",
        "user__email",
        "user__full_name",
        "listing__title",
    ]