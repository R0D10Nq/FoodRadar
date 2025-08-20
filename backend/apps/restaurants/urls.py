from __future__ import annotations

from django.urls import path
from .views import restaurants_list, restaurant_menu

urlpatterns = [
    path("restaurants", restaurants_list, name="restaurants-list"),
    path("restaurants/<int:id>/menu", restaurant_menu, name="restaurant-menu"),
]
