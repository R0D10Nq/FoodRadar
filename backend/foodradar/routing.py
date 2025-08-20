"""
Сборка WebSocket-маршрутов проекта. По MVP трекаем заказ: /ws/track/<order_id>
"""
from __future__ import annotations

from django.urls import path

# Заглушка: реальные консюмеры подцепим из apps.orders
try:
    from apps.orders.consumers import OrderTrackerConsumer  # type: ignore
except Exception:
    OrderTrackerConsumer = None  # type: ignore

websocket_urlpatterns = []
if OrderTrackerConsumer is not None:
    websocket_urlpatterns = [
        path("ws/track/<int:order_id>/", OrderTrackerConsumer.as_asgi(), name="ws-track-order"),
    ]
