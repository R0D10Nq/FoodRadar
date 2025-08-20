from __future__ import annotations

from django.urls import path
from .views import create_order, update_order_status, list_my_orders, get_order_detail

urlpatterns = [
    path("orders", create_order, name="orders-create"),
    path("orders/mine", list_my_orders, name="orders-list"),
    path("orders/<int:id>", get_order_detail, name="orders-detail"),
    path("orders/<int:id>/status", update_order_status, name="orders-status"),
]
