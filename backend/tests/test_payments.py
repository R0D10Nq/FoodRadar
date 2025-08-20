from __future__ import annotations

import pytest

from apps.orders.models import OrderStatus
from .factories import UserFactory, RestaurantFactory, OrderFactory


@pytest.mark.django_db
def test_pay_order_creates_payment_intent(api_client, auth_client, monkeypatch):
    from rest_framework import status
    client_user = UserFactory()
    resto = RestaurantFactory()
    order = OrderFactory(client=client_user, restaurant=resto, status=OrderStatus.CREATED)

    created_calls = {}

    class MockPI(dict):
        def __init__(self, pid: str):
            super().__init__(id=pid, client_secret="cs_test_123")

    # Мокаем Stripe
    class MockStripe:
        @staticmethod
        def create(**kwargs):  # type: ignore[no-redef]
            created_calls["payload"] = kwargs
            return MockPI("pi_test_1")

        @staticmethod
        def retrieve(pid: str):  # type: ignore[no-redef]
            return MockPI(pid)

    from apps.payments import views as pay_views

    monkeypatch.setattr(pay_views.stripe.PaymentIntent, "create", MockStripe.create)
    monkeypatch.setattr(pay_views.stripe.PaymentIntent, "retrieve", MockStripe.retrieve)

    c = auth_client(client_user)
    url = f"/api/v1/orders/{order.id}/pay"
    resp = c.post(url)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["payment_intent_id"] == "pi_test_1"
    order.refresh_from_db()
    assert order.status == OrderStatus.PENDING_PAYMENT
    assert order.stripe_payment_intent_id == "pi_test_1"
    # Убедимся, что сумма ушла в центах
    assert created_calls["payload"]["amount"] == int(order.total * 100)

    # Повторный вызов — должен пойти retrieve
    resp2 = c.post(url)
    assert resp2.status_code == status.HTTP_200_OK
    data2 = resp2.json()
    assert data2["payment_intent_id"] == "pi_test_1"


@pytest.mark.django_db
def test_stripe_webhook_marks_paid(api_client, monkeypatch):
    from rest_framework import status
    client_user = UserFactory()
    resto = RestaurantFactory()
    order = OrderFactory(client=client_user, restaurant=resto, status=OrderStatus.PENDING_PAYMENT)
    order.stripe_payment_intent_id = "pi_test_2"
    order.save(update_fields=["stripe_payment_intent_id"])

    event = {
        "type": "payment_intent.succeeded",
        "data": {"object": {"id": "pi_test_2", "metadata": {"order_id": str(order.id)}}},
    }

    from apps.payments import views as pay_views

    def _construct_event(payload, sig_header, secret):  # noqa: ARG001
        return event

    monkeypatch.setattr(pay_views.stripe.Webhook, "construct_event", staticmethod(_construct_event))

    resp = api_client.post(
        "/api/v1/stripe/webhook",
        data=b"{}",
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE="t_sig",
    )
    assert resp.status_code == status.HTTP_200_OK
    order.refresh_from_db()
    assert order.status == OrderStatus.PAID


@pytest.mark.django_db
def test_pay_order_forbidden_for_other_user(api_client, auth_client, monkeypatch):
    from rest_framework import status
    client_user = UserFactory()
    other = UserFactory()
    resto = RestaurantFactory()
    order = OrderFactory(client=client_user, restaurant=resto, status=OrderStatus.CREATED)

    from apps.payments import views as pay_views

    # Не важно, что вернет stripe — до него не дойдем
    monkeypatch.setattr(pay_views.stripe.PaymentIntent, "create", lambda **k: {"id": "pi_x"})

    c = auth_client(other)
    resp = c.post(f"/api/v1/orders/{order.id}/pay")
    assert resp.status_code == status.HTTP_403_FORBIDDEN
