from __future__ import annotations

from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import RegisterView

urlpatterns = [
    path("auth/register", RegisterView.as_view(), name="auth-register"),
    path("auth/token", TokenObtainPairView.as_view(), name="auth-token"),
    path("auth/token/refresh", TokenRefreshView.as_view(), name="auth-token-refresh"),
]
