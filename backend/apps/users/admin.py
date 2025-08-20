from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("-date_joined",)
    list_display = ("id", "email", "role", "is_active", "is_staff", "date_joined")
    search_fields = ("email", "phone")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Персональная информация"), {"fields": ("phone", "role")}),
        (_("Права"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Важные даты"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "role", "is_staff", "is_superuser"),
        }),
    )

    readonly_fields = ("date_joined",)

    def get_form(self, request, obj=None, **kwargs):  # noqa: D401
        """Подменяем username на email — классика для кастомной модели."""
        self.fieldsets
        return super().get_form(request, obj, **kwargs)
