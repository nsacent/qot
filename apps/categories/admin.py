from django.contrib import admin

from .models import Category, CategoryFilter, CategoryFilterOption


class CategoryFilterOptionInline(admin.TabularInline):
    model = CategoryFilterOption
    extra = 1


class CategoryFilterInline(admin.TabularInline):
    model = CategoryFilter
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "parent",
        "slug",
        "is_active",
        "sort_order",
        "created_at",
    ]
    list_filter = [
        "parent",
        "is_active",
        "created_at",
    ]
    search_fields = [
        "name",
        "slug",
        "parent__name",
    ]
    prepopulated_fields = {
        "slug": ("name",),
    }
    inlines = [
        CategoryFilterInline,
    ]


@admin.register(CategoryFilter)
class CategoryFilterAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "category",
        "key",
        "filter_type",
        "is_required",
        "is_searchable",
        "sort_order",
    ]
    list_filter = [
        "category",
        "filter_type",
        "is_required",
        "is_searchable",
    ]
    search_fields = [
        "name",
        "key",
        "category__name",
    ]
    prepopulated_fields = {
        "key": ("name",),
    }
    inlines = [
        CategoryFilterOptionInline,
    ]


@admin.register(CategoryFilterOption)
class CategoryFilterOptionAdmin(admin.ModelAdmin):
    list_display = [
        "label",
        "value",
        "category_filter",
        "is_active",
        "sort_order",
    ]
    list_filter = [
        "category_filter",
        "is_active",
    ]
    search_fields = [
        "label",
        "value",
        "category_filter__name",
    ]