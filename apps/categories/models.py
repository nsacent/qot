from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)

    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )

    icon = models.ImageField(
        upload_to="categories/icons/",
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["parent", "is_active"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.name


class CategoryFilter(models.Model):
    TYPE_TEXT = "text"
    TYPE_NUMBER = "number"
    TYPE_BOOLEAN = "boolean"
    TYPE_SELECT = "select"
    TYPE_MULTI_SELECT = "multi_select"

    TYPE_CHOICES = [
        (TYPE_TEXT, "Text"),
        (TYPE_NUMBER, "Number"),
        (TYPE_BOOLEAN, "Boolean"),
        (TYPE_SELECT, "Select"),
        (TYPE_MULTI_SELECT, "Multi Select"),
    ]

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="filters",
    )

    name = models.CharField(max_length=100)
    key = models.SlugField(max_length=120)
    filter_type = models.CharField(max_length=20, choices=TYPE_CHOICES)

    is_required = models.BooleanField(default=False)
    is_searchable = models.BooleanField(default=True)

    sort_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        unique_together = ["category", "key"]
        indexes = [
            models.Index(fields=["category", "key"]),
            models.Index(fields=["is_searchable"]),
        ]

    def __str__(self):
        return f"{self.category.name} - {self.name}"


class CategoryFilterOption(models.Model):
    category_filter = models.ForeignKey(
        CategoryFilter,
        on_delete=models.CASCADE,
        related_name="options",
    )

    label = models.CharField(max_length=100)
    value = models.CharField(max_length=100)

    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "label"]
        unique_together = ["category_filter", "value"]

    def __str__(self):
        return self.label