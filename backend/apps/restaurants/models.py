from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.conf import settings
import os
try:
    from django.contrib.gis.db import models as gis_models  # type: ignore
    from django.contrib.gis.geos import Point  # type: ignore
    _GIS_IMPORTS_OK = True
except Exception:  # pragma: no cover - окружение без GEOS/GDAL
    gis_models = None  # type: ignore
    Point = None  # type: ignore
    _GIS_IMPORTS_OK = False


class Restaurant(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="restaurants",
        verbose_name="Владелец",
    )
    name = models.CharField("Название", max_length=255)
    address = models.CharField("Адрес", max_length=500)
    lat = models.FloatField("Широта")
    lon = models.FloatField("Долгота")
    # Для PostGIS: географическая точка (включается если USE_GIS=1 и доступны зависимости)
    _USE_GIS = os.environ.get("USE_GIS", "0") == "1"
    if _GIS_IMPORTS_OK and _USE_GIS:  # pragma: no branch - конфигурируем поле при импорте модели
        location = gis_models.PointField("Геоточка", geography=True, srid=4326, null=True, blank=True)  # type: ignore[attr-defined]
    is_active = models.BooleanField("Активен", default=True)

    class Meta:
        verbose_name = "Ресторан"
        verbose_name_plural = "Рестораны"

    def save(self, *args, **kwargs):  # pragma: no cover - банальная сборка поля
        # Если поле location существует и доступен GeoPoint — соберем его из lat/lon
        if hasattr(self, "location") and Point is not None and self.lat is not None and self.lon is not None:
            try:
                self.location = Point(self.lon, self.lat)  # type: ignore[assignment]
            except Exception:
                pass
        super().save(*args, **kwargs)

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class Dish(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="dishes",
        verbose_name="Ресторан",
    )
    name = models.CharField("Название блюда", max_length=255)
    price = models.DecimalField("Цена", max_digits=10, decimal_places=2, default=Decimal("0.00"))
    allergens = models.JSONField("Аллергены", default=list, blank=True)
    is_available = models.BooleanField("В наличии", default=True)

    class Meta:
        verbose_name = "Блюдо"
        verbose_name_plural = "Блюда"

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name} ({self.restaurant_id})"
