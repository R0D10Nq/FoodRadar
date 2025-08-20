from __future__ import annotations

from django.urls import path
from .views import available_orders, accept_order, post_location

urlpatterns = [
    path("courier/orders/available", available_orders, name="courier-orders-available"),
    path("courier/orders/<int:id>/accept", accept_order, name="courier-orders-accept"),
    path("courier/location", post_location, name="courier-location"),
]
