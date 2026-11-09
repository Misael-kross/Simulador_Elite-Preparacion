from django.contrib import admin

from .models import AccessGrant, Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "is_active",
        "created_at",
    )

    search_fields = (
        "code",
        "name",
    )

    list_filter = (
        "is_active",
    )

    ordering = (
        "code",
    )


@admin.register(AccessGrant)
class AccessGrantAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "product",
        "starts_at",
        "expires_at",
        "is_active",
        "is_valid_display",
    )

    search_fields = (
        "user__username",
        "product__code",
        "product__name",
    )

    list_filter = (
        "product",
        "is_active",
    )

    autocomplete_fields = (
        "user",
        "product",
    )

    @admin.display(boolean=True, description="Vigente")
    def is_valid_display(self, obj):
        return obj.is_valid