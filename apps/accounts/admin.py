from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, UserFollow, UserProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["-date_joined"]
    list_display = [
        "phone",
        "email",
        "full_name",
        "role",
        "is_active",
        "is_verified",
        "phone_verified_at",
        "email_verified_at",
        "is_banned",
        "is_staff",
        "date_joined",
    ]
    list_filter = [
        "role",
        "is_active",
        "is_verified",
        "is_banned",
        "is_staff",
        "date_joined",
    ]
    search_fields = [
        "phone",
        "email",
        "full_name",
    ]

    fieldsets = (
        (
            "Login Details",
            {
                "fields": (
                    "phone",
                    "email",
                    "password",
                )
            },
        ),
        (
            "Personal Information",
            {
                "fields": (
                    "full_name",
                )
            },
        ),
        (
            "Role & Status",
            {
                "fields": (
                    "role",
                    "is_active",
                    "is_verified",
                    "phone_verified_at",
                    "email_verified_at",
                    "is_banned",
                    "banned_reason",
                    "is_staff",
                    "is_superuser",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Important Dates",
            {
                "fields": (
                    "last_login",
                    "date_joined",
                    "updated_at",
                )
            },
        ),
    )

    readonly_fields = [
        "last_login",
        "date_joined",
        "phone_verified_at",
        "email_verified_at",
        "updated_at",
    ]

    add_fieldsets = (
        (
            "Create User",
            {
                "classes": ("wide",),
                "fields": (
                    "phone",
                    "email",
                    "full_name",
                    "password1",
                    "password2",
                    "role",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "business_name",
        "timezone",
        "trust_score",
        "total_listings",
        "created_at",
    ]
    search_fields = [
        "user__phone",
        "user__email",
        "user__full_name",
        "business_name",
    ]
    list_filter = [
        "timezone",
        "created_at",
    ]
    readonly_fields = [
        "created_at",
        "updated_at",
    ]


@admin.register(UserFollow)
class UserFollowAdmin(admin.ModelAdmin):
    list_display = ["follower", "following", "created_at"]
    search_fields = [
        "follower__full_name",
        "follower__email",
        "following__full_name",
        "following__email",
    ]
    readonly_fields = ["created_at"]
