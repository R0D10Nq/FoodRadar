from __future__ import annotations

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .serializers import CourierLocationSerializer
from .models import CourierLocation
from apps.users.models import UserRole
from apps.orders.models import Order, OrderStatus
from apps.orders.tasks import broadcast_order_event
try:
    from django.contrib.gis.geos import Point as GeoPoint
except Exception:  # pragma: no cover - окружение без GEOS
    GeoPoint = None  # type: ignore
try:
    from django.contrib.gis.db.models.functions import Distance  # type: ignore
except Exception:  # pragma: no cover - окружение без GIS
    Distance = None  # type: ignore
import math


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def available_orders(request):
    """Доступные заказы для курьера, отсортированные по дистанции до ресторана (если есть GPS)."""
    user = request.user
    if getattr(user, "role", None) != UserRole.COURIER:
        return Response({"detail": "Только курьеры могут смотреть доступные заказы."}, status=status.HTTP_403_FORBIDDEN)

    qs = (
        Order.objects.filter(
            status__in=[OrderStatus.READY_FOR_PICKUP, OrderStatus.RESTAURANT_CONFIRMED],
            courier__isnull=True,
        )
        .select_related("restaurant")
    )

    last_loc = CourierLocation.objects.filter(courier=user).order_by("-ts").first()
    if last_loc and last_loc.lon is not None and last_loc.lat is not None:
        user_point = GeoPoint(last_loc.lon, last_loc.lat, srid=4326) if GeoPoint else None
        try:
            # Предпочитаем PostGIS: быстро и индексно
            if Distance and user_point is not None:
                qs = qs.annotate(distance=Distance("restaurant__location", user_point)).order_by("distance")
                use_python_sort = False
            else:
                raise Exception("GIS unavailable")
        except Exception:
            # Фолбэк без PostGIS: сортируем по Хаверсину на питоне
            use_python_sort = True
        if use_python_sort:
            def _haversine_km(lat1, lon1, lat2, lon2):
                R = 6371.0
                phi1 = math.radians(lat1)
                phi2 = math.radians(lat2)
                dphi = math.radians(lat2 - lat1)
                dlambda = math.radians(lon2 - lon1)
                a = math.sin(dphi/2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2) ** 2
                return 2 * R * math.asin(math.sqrt(a))

            with_loc = qs.select_related("restaurant").only(
                "id", "restaurant__id", "restaurant__name", "restaurant__lat", "restaurant__lon", "total", "status"
            )[:200]  # ограничим, чтобы не выкачивать лишнее
            enriched = []
            for o in with_loc:
                r = o.restaurant
                if r and r.lat is not None and r.lon is not None:
                    dist_km = _haversine_km(last_loc.lat, last_loc.lon, r.lat, r.lon)
                else:
                    dist_km = float("inf")
                enriched.append((dist_km, o))
            enriched.sort(key=lambda x: x[0])
            qs = [o for _, o in enriched]
    else:
        qs = qs.order_by("-created_at")

    results = []
    # Если qs — список (фолбэк) или QuerySet — обрабатываем одинаково
    sliced = qs[:50] if not isinstance(qs, list) else qs[:50]
    for o in sliced:
        dist_km = None
        d = getattr(o, "distance", None)
        if d is not None:
            try:
                dist_km = round(d.km, 3)
            except Exception:  # pragma: no cover
                pass
        # Для фолбэка пометим расстояние, если его посчитали вручную
        if dist_km is None and last_loc and hasattr(o, "restaurant") and o.restaurant and o.restaurant.lat is not None:
            try:
                # При фолбэке уже отсортировано; можно пересчитать аккуратно
                def _hv(lat1, lon1, lat2, lon2):
                    R = 6371.0
                    from math import radians, sin, cos, asin, sqrt
                    phi1, phi2 = radians(lat1), radians(lat2)
                    dphi = radians(lat2 - lat1)
                    dl = radians(lon2 - lon1)
                    a = sin(dphi/2)**2 + cos(phi1)*cos(phi2)*sin(dl/2)**2
                    return 2 * R * asin(sqrt(a))
                dist_km = round(_hv(last_loc.lat, last_loc.lon, o.restaurant.lat, o.restaurant.lon), 3)
            except Exception:
                pass
        results.append(
            {
                "id": o.id,
                "restaurant_id": o.restaurant_id,
                "restaurant_name": o.restaurant.name,
                "total": str(o.total),
                "status": o.status,
                "distance_km": dist_km,
            }
        )
    return Response({"results": results})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def accept_order(request, id: int):  # noqa: A002
    """Курьер пытается взять заказ. Делаем гонку безопасной атомарным UPDATE."""
    user = request.user
    if getattr(user, "role", None) != UserRole.COURIER:
        return Response({"detail": "Только курьер может принять заказ."}, status=status.HTTP_403_FORBIDDEN)

    updated = (
        Order.objects.filter(
            id=id,
            courier__isnull=True,
            status__in=[OrderStatus.READY_FOR_PICKUP, OrderStatus.RESTAURANT_CONFIRMED],
        )
        .update(courier=user, status=OrderStatus.ACCEPTED)
    )
    if updated == 0:
        return Response({"detail": "Заказ уже кем-то принят или недоступен."}, status=status.HTTP_409_CONFLICT)

    # Подтянем запись и сообщим по WS
    order = Order.objects.select_related("restaurant").get(pk=id)
    broadcast_order_event.delay(order.id, {"type": "accepted", "order_id": order.id, "courier_id": user.id})
    return Response(
        {
            "order_id": order.id,
            "status": order.status,
            "courier_id": user.id,
            "restaurant": {"id": order.restaurant_id, "name": order.restaurant.name},
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def post_location(request):
    """Прием GPS точки курьера. Лаконично, валидно, по делу."""
    serializer = CourierLocationSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    obj = serializer.save()

    # Если это курьер — пушим координаты всем его активным заказам, чтобы фронт видел live-трекинг
    user = request.user
    if getattr(user, "role", None) == UserRole.COURIER:
        active_orders = (
            Order.objects.filter(courier=user, status__in=[OrderStatus.ACCEPTED, OrderStatus.IN_TRANSIT])
            .only("id", "status")
        )
        for order in active_orders:
            # Лёгкий автопереход: как только курьер поехал — статус IN_TRANSIT
            if order.status == OrderStatus.ACCEPTED:
                Order.objects.filter(id=order.id, status=OrderStatus.ACCEPTED).update(status=OrderStatus.IN_TRANSIT)
                order.status = OrderStatus.IN_TRANSIT
                broadcast_order_event.delay(order.id, {"type": "in_transit", "order_id": order.id})

            broadcast_order_event.delay(
                order.id,
                {
                    "type": "courier_location",
                    "order_id": order.id,
                    "lat": obj.lat,
                    "lon": obj.lon,
                    "ts": obj.ts.isoformat(),
                },
            )

    return Response(CourierLocationSerializer(obj).data, status=status.HTTP_201_CREATED)
