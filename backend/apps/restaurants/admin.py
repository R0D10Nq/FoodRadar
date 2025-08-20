from __future__ import annotations

from django.contrib import admin
from .models import Restaurant, Dish


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "owner", "is_active")
    search_fields = ("name", "address")
    list_filter = ("is_active",)


@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "restaurant", "price", "is_available")
    search_fields = ("name",)
    list_filter = ("is_available",)
