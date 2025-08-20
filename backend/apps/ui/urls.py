from __future__ import annotations

from django.urls import path
from django.views.generic.base import RedirectView
from .views import index, landing

urlpatterns = [
    # Лендинг — лаконичная главная с CTA
    path("", landing, name="ui-landing"),
    # Приложение — минимальный интерфейс для клика по API
    path("app/", index, name="ui-index"),
    # Favicon: редиректим на статический SVG, чтобы убрать 404 в логах dev-сервера
    path("favicon.ico", RedirectView.as_view(url="/static/favicon.svg"), name="ui-favicon"),
]
