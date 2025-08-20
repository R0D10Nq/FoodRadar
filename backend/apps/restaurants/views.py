from __future__ import annotations

from typing import List

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status
from django.shortcuts import get_object_or_404
try:
    from django.contrib.gis.geos import Point as GeoPoint
except Exception:  # pragma: no cover - окружение без GEOS
    GeoPoint = None  # type: ignore
try:
    from django.contrib.gis.measure import D  # type: ignore
    from django.contrib.gis.db.models.functions import Distance  # type: ignore
except Exception:  # pragma: no cover - окружение без GIS
    D = None  # type: ignore
    Distance = None  # type: ignore
import math

from .models import Restaurant, Dish
from .serializers import RestaurantListSerializer, RestaurantMenuSerializer


@api_view(["GET"])
@permission_classes([AllowAny])
def restaurants_list(request: Request):
    """
    Список активных ресторанов рядом с точкой (lat, lon) в радиусе (км).
    Пример: /api/v1/restaurants?lat=55.75&lon=37.62&radius=5
    Если координаты не заданы — вернем все активные без сортировки по дистанции.
    """
    lat = request.query_params.get("lat")
    lon = request.query_params.get("lon")
    radius = float(request.query_params.get("radius", 5))

    qs = Restaurant.objects.filter(is_active=True)

    if lat and lon:
        try:
            lat_f = float(lat)
            lon_f = float(lon)
        except ValueError:
            return Response({"detail": "lat/lon должны быть числами"}, status=status.HTTP_400_BAD_REQUEST)
        user_point = GeoPoint(lon_f, lat_f, srid=4326) if GeoPoint else None
        used_fallback = False
        if Distance and D and user_point is not None:
            try:
                qs = (
                    qs.filter(location__isnull=False)
                    .annotate(distance=Distance("location", user_point))
                    .filter(location__distance_lte=(user_point, D(km=radius)))
                    .order_by("distance")
                )
            except Exception:
                used_fallback = True
        else:
            used_fallback = True

        if used_fallback:
            # Фолбэк: фильтруем и сортируем по Хаверсину на питоне
            def _haversine_km(lat1, lon1, lat2, lon2):
                R = 6371.0
                phi1, phi2 = math.radians(lat1), math.radians(lat2)
                dphi = math.radians(lat2 - lat1)
                dl = math.radians(lon2 - lon1)
                a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dl/2)**2
                return 2 * R * math.asin(math.sqrt(a))

            base = qs.only("id", "name", "lat", "lon", "address", "is_active")
            enriched = []
            for r in base:
                if r.lat is None or r.lon is None:
                    continue
                dist_km = _haversine_km(lat_f, lon_f, r.lat, r.lon)
                if dist_km <= radius:
                    # Проставим distance в МЕТРАХ для сериализатора (он приведет к км)
                    try:
                        setattr(r, "distance", float(dist_km) * 1000.0)
                    except Exception:
                        pass
                    enriched.append((dist_km, r))
            enriched.sort(key=lambda x: x[0])
            qs = [r for _, r in enriched]
    data = RestaurantListSerializer(qs, many=True).data if not isinstance(qs, list) else RestaurantListSerializer(qs, many=True).data
    return Response({"results": data})


@api_view(["GET"])
@permission_classes([AllowAny])
def restaurant_menu(request: Request, id: int):  # noqa: A002 - коротко и по делу
    """
    Меню ресторана. Фильтрация по аллергенам: exclude_allergens=peanut,gluten
    """
    restaurant = get_object_or_404(Restaurant.objects.filter(is_active=True), pk=id)
    exclude_raw = request.query_params.get("exclude_allergens", "")
    exclude: List[str] = [x.strip() for x in exclude_raw.split(",") if x.strip()]

    dishes_qs = restaurant.dishes.filter(is_available=True)
    # Для JSONB c массивом строк самый простой путь — фильтровать на приложении. Для MVP окей.
    if exclude:
        dishes = [d for d in dishes_qs if not set(map(str.lower, d.allergens or [])).intersection(set(map(str.lower, exclude)))]
    else:
        dishes = list(dishes_qs)

    # Вручную собираем сериализатор меню (включая вложенные блюда)
    restaurant_data = RestaurantMenuSerializer(restaurant).data
    restaurant_data["dishes"] = [
        {"id": d.id, "name": d.name, "price": d.price, "allergens": d.allergens, "is_available": d.is_available}
        for d in dishes
    ]
    return Response(restaurant_data)
