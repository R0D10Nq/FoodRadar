from __future__ import annotations

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status
from django.shortcuts import get_object_or_404

from apps.users.models import UserRole
from .models import Order, OrderStatus
from .serializers import (
    OrderCreateSerializer,
    OrderSerializer,
    OrderStatusUpdateSerializer,
)
from .tasks import broadcast_order_event


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_order(request: Request):
    """
    Создание заказа (корзина). Вход: restaurant_id, items:[{dish_id, qty}].
    """
    serializer = OrderCreateSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    order = serializer.save()
    data = OrderSerializer(order).data
    # Расшарим событие для подписчиков, что заказ создан
    broadcast_order_event.delay(order.id, {"type": "created", "order": data})
    return Response(data, status=status.HTTP_201_CREATED)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_order_status(request: Request, id: int):  # noqa: A002
    """
    Смена статуса заказа. Права:
    - Ресторан (владелец ресторана): restaurant_confirmed, ready_for_pickup, canceled
    - Курьер (назначен на заказ): in_transit, delivered
    - Клиент (создатель): canceled (пока заказ не оплачен)
    """
    order = get_object_or_404(Order, pk=id)
    serializer = OrderStatusUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    new_status: str = serializer.validated_data["status"]

    user = request.user
    role = getattr(user, "role", None)

    allowed = False
    if role == UserRole.RESTAURANT and order.restaurant.owner_id == user.id:
        allowed = new_status in {
            OrderStatus.RESTAURANT_CONFIRMED,
            OrderStatus.READY_FOR_PICKUP,
            OrderStatus.CANCELED,
        }
    elif role == UserRole.COURIER and order.courier_id == user.id:
        allowed = new_status in {
            OrderStatus.IN_TRANSIT,
            OrderStatus.DELIVERED,
        }
    elif role == UserRole.CLIENT and order.client_id == user.id:
        if order.status in {OrderStatus.CREATED, OrderStatus.PENDING_PAYMENT}:
            allowed = new_status == OrderStatus.CANCELED

    if not allowed:
        return Response({"detail": "Недостаточно прав или недопустимый переход статуса."}, status=status.HTTP_403_FORBIDDEN)

    order.status = new_status
    order.save(update_fields=["status", "updated_at"])
    payload = {"type": "status", "order_id": order.id, "status": order.status}
    broadcast_order_event.delay(order.id, payload)
    return Response(OrderSerializer(order).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_my_orders(request: Request):
    """Список заказов текущего пользователя (клиента). Поддерживает фильтр по статусу и простую пагинацию."""
    user = request.user
    qs = Order.objects.filter(client_id=user.id).order_by("-created_at")
    status_filter = request.query_params.get("status")
    if status_filter:
        qs = qs.filter(status=status_filter)

    # Простая пагинация без тяжелых зависимостей
    def _to_int(v: str | None, d: int, lo: int, hi: int) -> int:
        try:
            x = int(v) if v is not None else d
        except Exception:
            x = d
        return max(lo, min(hi, x))

    page = _to_int(request.query_params.get("page"), 1, 1, 10_000)
    page_size = _to_int(request.query_params.get("page_size"), 20, 1, 100)
    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    data = OrderSerializer(qs[start:end], many=True).data
    return Response({
        "count": total,
        "page": page,
        "page_size": page_size,
        "results": data,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_order_detail(request: Request, id: int):  # noqa: A002
    """Детали заказа. Доступ: клиент-владелец, ресторан-владелец, назначенный курьер, админ."""
    order = get_object_or_404(Order, pk=id)
    user = request.user
    role = getattr(user, "role", None)
    allowed = False
    if order.client_id == user.id:
        allowed = True
    elif order.courier_id == user.id:
        allowed = True
    elif role == UserRole.RESTAURANT and order.restaurant.owner_id == user.id:
        allowed = True
    elif role == UserRole.ADMIN:
        allowed = True
    if not allowed:
        return Response({"detail": "Недостаточно прав для просмотра заказа."}, status=status.HTTP_403_FORBIDDEN)
    return Response(OrderSerializer(order).data)
