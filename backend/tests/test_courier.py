from __future__ import annotations

import pytest
from django.utils import timezone

from apps.users.models import UserRole
from apps.orders.models import OrderStatus
from .factories import (
    CourierFactory,
    UserFactory,
    RestaurantFactory,
    OrderFactory,
    CourierLocationFactory,
)


@pytest.mark.django_db
def test_courier_accept_order_success(api_client, auth_client, monkeypatch):
    from rest_framework import status  # локальный импорт, чтобы не ломать init Django
    courier = CourierFactory()
    client_user = UserFactory(role=UserRole.CLIENT)
    resto = RestaurantFactory(lat=55.75, lon=37.61)
    order = OrderFactory(client=client_user, restaurant=resto, status=OrderStatus.READY_FOR_PICKUP)

    # Заглушка WS-рассылки
    from apps.orders import tasks as order_tasks

    monkeypatch.setattr(order_tasks.broadcast_order_event, "delay", lambda *a, **k: None)

    c = auth_client(courier)
    url = f"/api/v1/courier/orders/{order.id}/accept"
    resp = c.post(url)
    assert resp.status_code == status.HTTP_200_OK
    order.refresh_from_db()
    assert order.courier_id == courier.id
    assert order.status == OrderStatus.ACCEPTED

    # Второй курьер получит 409
    other = CourierFactory()
    c2 = auth_client(other)
    resp2 = c2.post(url)
    assert resp2.status_code == status.HTTP_409_CONFLICT


@pytest.mark.django_db
def test_available_orders_sorted_by_distance(api_client, auth_client):
    from rest_framework import status
    courier = CourierFactory()
    # Последняя локация курьера — центр
    CourierLocationFactory(courier=courier, lat=55.75, lon=37.61)

    # Ближний ресторан
    near = RestaurantFactory(lat=55.751, lon=37.62)
    # Дальний ресторан
    far = RestaurantFactory(lat=55.0, lon=38.0)

    o1 = OrderFactory(restaurant=near, status=OrderStatus.READY_FOR_PICKUP)
    o2 = OrderFactory(restaurant=far, status=OrderStatus.READY_FOR_PICKUP)

    c = auth_client(courier)
    resp = c.get("/api/v1/courier/orders/available")
    assert resp.status_code == status.HTTP_200_OK
    results = resp.json()["results"]
    assert len(results) >= 2
    # Первый должен быть ближний
    assert results[0]["id"] in {o1.id, o2.id}
    assert results[0]["id"] == o1.id
    assert results[0]["distance_km"] is not None


@pytest.mark.django_db
def test_post_location_switches_in_transit(api_client, auth_client, monkeypatch):
    from rest_framework import status
    courier = CourierFactory()
    client_user = UserFactory(role=UserRole.CLIENT)
    resto = RestaurantFactory(lat=55.75, lon=37.61)
    order = OrderFactory(client=client_user, restaurant=resto, status=OrderStatus.ACCEPTED)
    order.courier_id = courier.id
    order.save(update_fields=["courier"])  # назначили курьера

    from apps.orders import tasks as order_tasks

    monkeypatch.setattr(order_tasks.broadcast_order_event, "delay", lambda *a, **k: None)

    c = auth_client(courier)
    resp = c.post("/api/v1/courier/location", {"lat": 55.7512, "lon": 37.6184})
    assert resp.status_code == status.HTTP_201_CREATED
    order.refresh_from_db()
    assert order.status == OrderStatus.IN_TRANSIT
