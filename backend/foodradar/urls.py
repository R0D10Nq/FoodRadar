from __future__ import annotations

"""
Глобальные URL. Все API висят под /api/v1/
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    # UI (простая витрина для клика через браузер)
    path("", include("apps.ui.urls")),

    path("admin/", admin.site.urls),

    # API v1
    path("api/v1/", include("apps.users.urls")),
    path("api/v1/", include("apps.restaurants.urls")),
    path("api/v1/", include("apps.orders.urls")),
    path("api/v1/", include("apps.courier.urls")),
    path("api/v1/", include("apps.payments.urls")),

    # OpenAPI схема и UI
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
