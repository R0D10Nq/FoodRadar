from __future__ import annotations

from django.conf import settings
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse


def index(request: HttpRequest) -> HttpResponse:
    """
    Простейшая витрина UI для локального демо.
    Никакого SPA — один шаблон + немного JS, чтобы покликать API как обычный пользователь.
    """
    ctx = {
        "stripe_pk": getattr(settings, "STRIPE_PUBLISHABLE_KEY", ""),
        "api_base": "/api/v1",
    }
    return render(request, "ui/index.html", ctx)


def landing(request: HttpRequest) -> HttpResponse:
    """
    Простой лендинг с CTA. Никаких сложностей — один шаблон.
    """
    ctx = {
        "stripe_pk": getattr(settings, "STRIPE_PUBLISHABLE_KEY", ""),
        "api_base": "/api/v1",
    }
    return render(request, "ui/landing.html", ctx)
