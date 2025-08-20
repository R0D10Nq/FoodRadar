from __future__ import annotations

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
import stripe
import decimal

from apps.orders.models import Order, OrderStatus
from apps.orders.tasks import broadcast_order_event

stripe.api_key = settings.STRIPE_SECRET_KEY

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def pay_order(request, id: int):  # noqa: A002
    """Создаем или возвращаем PaymentIntent для заказа. Валюта — USD, MVP."""
    user = request.user
    order = get_object_or_404(Order, pk=id)
    if order.client_id != user.id:
        return Response({"detail": "Можно оплатить только свой заказ."}, status=status.HTTP_403_FORBIDDEN)
    if order.status not in {OrderStatus.CREATED, OrderStatus.PENDING_PAYMENT}:
        return Response({"detail": "Неверный статус заказа для оплаты."}, status=status.HTTP_400_BAD_REQUEST)

    # Stripe ожидает integer amount в центах
    total: decimal.Decimal = order.total or decimal.Decimal("0.00")
    amount_cents = int(total * 100)
    if amount_cents <= 0:
        return Response({"detail": "Сумма заказа некорректна."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        if order.stripe_payment_intent_id:
            pi = stripe.PaymentIntent.retrieve(order.stripe_payment_intent_id)
        else:
            pi = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency="usd",
                metadata={"order_id": str(order.id)},
                automatic_payment_methods={"enabled": True},
            )
            order.stripe_payment_intent_id = pi["id"]
            order.status = OrderStatus.PENDING_PAYMENT
            order.save(update_fields=["stripe_payment_intent_id", "status", "updated_at"])
            broadcast_order_event.delay(order.id, {"type": "payment_created", "order_id": order.id})
    except Exception as e:  # pragma: no cover - внешнее API
        return Response({"detail": f"Stripe error: {e}"}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        "order_id": order.id,
        "payment_intent_id": pi["id"],
        "client_secret": pi.get("client_secret"),
        "status": order.status,
    })


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_exempt
def stripe_webhook(request):
    """Webhook Stripe: обновляем статус заказа по PaymentIntentSucceeded/Failed."""
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
    try:
        event = stripe.Webhook.construct_event(payload=payload, sig_header=sig_header, secret=endpoint_secret)
    except Exception as e:  # pragma: no cover
        return Response({"detail": f"Invalid webhook: {e}"}, status=status.HTTP_400_BAD_REQUEST)

    if event["type"] == "payment_intent.succeeded":
        pi = event["data"]["object"]
        order_id = int(pi["metadata"].get("order_id", 0)) if pi.get("metadata") else 0
        if order_id:
            try:
                order = Order.objects.get(pk=order_id, stripe_payment_intent_id=pi["id"])  # type: ignore[index]
                order.status = OrderStatus.PAID
                order.save(update_fields=["status", "updated_at"])
                broadcast_order_event.delay(order.id, {"type": "paid", "order_id": order.id})
            except Order.DoesNotExist:  # pragma: no cover
                pass
    elif event["type"] in {"payment_intent.payment_failed", "payment_intent.canceled"}:
        pi = event["data"]["object"]
        order_id = int(pi["metadata"].get("order_id", 0)) if pi.get("metadata") else 0
        if order_id:
            try:
                order = Order.objects.get(pk=order_id, stripe_payment_intent_id=pi["id"])  # type: ignore[index]
                # Не меняем на canceled автоматически, оставим на усмотрение клиента/ресторана
                broadcast_order_event.delay(order.id, {"type": "payment_failed", "order_id": order.id})
            except Order.DoesNotExist:  # pragma: no cover
                pass

    return Response({"received": True})
