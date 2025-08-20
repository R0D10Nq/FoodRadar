"""
Настройки Django-проекта FoodRadar. Комментарии по-русски, без фанатизма.
"""
from __future__ import annotations

import os
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Env ---
env = environ.Env(
    DJANGO_DEBUG=(bool, False),
)
# Читаем .env, если он есть
env_file = BASE_DIR.parent / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

# Базовые настройки
SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-dev-key-change-me")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = [h.strip() for h in str(env("DJANGO_ALLOWED_HOSTS", default="*")).split(",")]

# Локаль
LANGUAGE_CODE = "ru"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Флаги окружения
USE_GIS = env("USE_GIS", default="0") == "1"

# Приложения
INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Сторонние
    "rest_framework",
    "rest_framework.authtoken",
    "rest_framework_simplejwt",
    "django_filters",
    "channels",
    "corsheaders",
    "drf_spectacular",

    # Наши
    "apps.geo",
    "apps.users",
    "apps.restaurants",
    "apps.orders",
    "apps.courier",
    "apps.payments",
    "apps.ui",
]

# Включаем GeoDjango только если явно разрешено и окружение готово
if USE_GIS:
    INSTALLED_APPS.insert(7, "django.contrib.gis")  # рядом со стандартными Django app'ами

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "foodradar.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "foodradar.wsgi.application"
ASGI_APPLICATION = "foodradar.asgi.application"

# БД: поддерживаем DATABASE_URL (12-factor). По умолчанию — SQLite (легкий локальный старт).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(BASE_DIR / "db.sqlite3"),
    }
}

# Если задан DATABASE_URL — используем его. Принудительно меняем движок на PostGIS при postgresql.
_db_url = env("DATABASE_URL", default=None)
if _db_url:
    db_cfg = env.db("DATABASE_URL")
    # Если это стандартный postgres — подменим на gis-бэкэнд
    if db_cfg.get("ENGINE", "").startswith("django.db.backends.postgresql"):
        db_cfg["ENGINE"] = "django.contrib.gis.db.backends.postgis"
    DATABASES["default"] = db_cfg
elif USE_GIS:
    # Если явно хотим GIS — ожидаем Postgres параметры из env
    DATABASES["default"] = {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": env("POSTGRES_DB", default="foodradar"),
        "USER": env("POSTGRES_USER", default="postgres"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="postgres"),
        "HOST": env("POSTGRES_HOST", default="localhost"),
        "PORT": env("POSTGRES_PORT", default="5432"),
    }

# Каналы (WebSocket): если нет Redis — используем InMemory, чтобы локально всё работало без докера
_redis_url = env("CHANNEL_REDIS_URL", default=None)
if _redis_url:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [_redis_url]},
        }
    }
else:
    CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
    }

# Celery: если нет Redis — гоняем задачи синхронно (eager), это облегчает локальные прогоны без докера
CELERY_BROKER_URL = env("REDIS_URL", default=None) or env("CHANNEL_REDIS_URL", default=None)
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_TASK_ALWAYS_EAGER = not bool(CELERY_BROKER_URL)

# DRF
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
        "rest_framework.filters.SearchFilter",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# Пользовательская модель
AUTH_USER_MODEL = "users.User"

# Статика/медиа
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# CORS — для удобства в деве разрешим всё
CORS_ALLOW_ALL_ORIGINS = True

# Stripe
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", default="")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", default="")
STRIPE_PUBLISHABLE_KEY = env("STRIPE_PUBLISHABLE_KEY", default="")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Логи — минимально, но полезно
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}

# OpenAPI/Swagger — чтобы красиво показать API
SPECTACULAR_SETTINGS = {
    "TITLE": "FoodRadar API",
    "DESCRIPTION": "Мини-UberEats: рестораны, меню, заказы, курьеры, Stripe, трекинг.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# Sentry (опционально)
SENTRY_DSN = env("SENTRY_DSN", default="")

try:
    import sentry_sdk  # type: ignore
    from sentry_sdk.integrations.django import DjangoIntegration  # type: ignore
    from sentry_sdk.integrations.celery import CeleryIntegration  # type: ignore
except Exception:  # pragma: no cover - sentry не установлен
    sentry_sdk = None  # type: ignore

if SENTRY_DSN and sentry_sdk:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        traces_sample_rate=float(env("SENTRY_TRACES_SAMPLE_RATE", default=0.0)),
        profiles_sample_rate=float(env("SENTRY_PROFILES_SAMPLE_RATE", default=0.0)),
        send_default_pii=True,
        environment=env("SENTRY_ENVIRONMENT", default=("development" if DEBUG else "production")),
    )
