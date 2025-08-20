from __future__ import annotations

from django.urls import path
from .views import pay_order, stripe_webhook

urlpatterns = [
    path("orders/<int:id>/pay", pay_order, name="orders-pay"),
    path("stripe/webhook", stripe_webhook, name="stripe-webhook"),
]
