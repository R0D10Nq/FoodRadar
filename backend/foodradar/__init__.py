"""
Инициализация проекта. Здесь же подключаем Celery, чтобы воркер подхватывал настройки Django.
"""
from .celery import app as celery_app  # noqa: F401
