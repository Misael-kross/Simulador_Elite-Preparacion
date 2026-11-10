from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from access_control.models import AccessGrant
from .models import ActiveSession, User


class AccessGrantInline(admin.TabularInline):
    model = AccessGrant
    extra = 1

    autocomplete_fields = (
        "product",
    )

    fields = (
        "product",
        "starts_at",
        "expires_at",
        "is_active",
        "notes",
    )


@admin.register(User)
class EliteUserAdmin(UserAdmin):
    fieldsets = tuple(
        section
        for section in UserAdmin.fieldsets
        if section[0] != "Personal info"
    )

    add_fieldsets = UserAdmin.add_fieldsets

    list_display = (
        "username",
        "is_active",
        "is_staff",
        "is_superuser",
        "last_login",
    )

    search_fields = ("username",)
    ordering = ("username",)

    inlines = (
        AccessGrantInline,
    )


@admin.action(description="Forzar cierre de las sesiones seleccionadas")
def terminate_sessions(modeladmin, request, queryset):
    count = 0

    for active_session in queryset:
        active_session.terminate()
        count += 1

    modeladmin.message_user(
        request,
        f"{count} sesión(es) cerrada(s).",
    )


@admin.register(ActiveSession)
class ActiveSessionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "user__username",
    )

    readonly_fields = (
        "user",
        "session_key",
        "created_at",
        "updated_at",
    )

    actions = (
        terminate_sessions,
    )