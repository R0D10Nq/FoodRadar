"""
Celery-конфиг. Ничего сверхъестественного: брокер Redis, автодискавер задач по приложениям.
"""
from __future__ import annotations

import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "foodradar.settings")

app = Celery("foodradar")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
