"""
ASGI-инициализация с поддержкой HTTP и WebSocket через Channels.
"""
from __future__ import annotations

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "foodradar.settings")

django_asgi_app = get_asgi_application()

# Импорт маршрутов WebSocket (ленивая загрузка, чтобы избежать циклов импортов)
try:
    from .routing import websocket_urlpatterns  # type: ignore
except Exception:  # в ранней стадии проект может быть без маршрутов
    websocket_urlpatterns = []

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
})
