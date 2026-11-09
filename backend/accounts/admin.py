from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class EliteUserAdmin(UserAdmin):
    fieldsets = tuple(
        section
        for section in UserAdmin.fieldsets
        if section[0] != "Personal info"
    )

    list_display = (
        "username",
        "is_active",
        "is_staff",
        "is_superuser",
        "last_login",
    )

    search_fields = ("username",)
    ordering = ("username",)