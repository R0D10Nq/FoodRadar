from __future__ import annotations

import pytest

"""
Тестовые фикстуры.

Важно:
- DRF/JWT не импортируем на уровне модуля: импорты — внутри фикстур.
- Инициализацию Django, создание/очистку тестовой БД выполняет pytest-django
  (подключен явным образом через pytest.ini, см. addopts = -p django).
"""


@pytest.fixture
def api_client():
    # Импортируем тут, когда Django уже сконфигурирован плагином pytest-django
    from rest_framework.test import APIClient  # noqa: WPS433 — локальный импорт осознан

    return APIClient()


@pytest.fixture
def auth_client(api_client):
    """Фикстура-генератор авторизованного клиента по юзеру."""
    def _make(user) -> APIClient:
        # Локально импортируем JWT, чтобы избежать ранних обращений к settings
        from rest_framework_simplejwt.tokens import RefreshToken  # noqa: WPS433

        token = str(RefreshToken.for_user(user).access_token)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return api_client

    return _make
