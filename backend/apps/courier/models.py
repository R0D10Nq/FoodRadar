from __future__ import annotations

from django.db import models
from django.conf import settings


class CourierLocation(models.Model):
    """GPS-точка курьера. Минимум полей — то, что реально нужно под трекинг."""

    courier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="locations",
        verbose_name="Курьер",
    )
    lat = models.FloatField("Широта")
    lon = models.FloatField("Долгота")
    ts = models.DateTimeField("Метка времени", auto_now_add=True)

    class Meta:
        verbose_name = "Локация курьера"
        verbose_name_plural = "Локации курьеров"
        indexes = [
            # btree (courier_id, ts DESC) — как и просили
            models.Index(fields=["courier", "-ts"], name="idx_courier_ts_desc"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.courier_id} @ {self.lat},{self.lon} {self.ts}"
