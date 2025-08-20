"""
WSGI точка — пусть будет на всякий, хотя у нас ASGI через daphne.
"""
from __future__ import annotations

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "foodradar.settings")

application = get_wsgi_application()
