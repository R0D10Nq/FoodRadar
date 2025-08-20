from __future__ import annotations

from celery import shared_task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


@shared_task
def broadcast_order_event(order_id: int, payload: dict) -> None:
    """Кидаем событие в WS-группу заказа. Лаконично, по-девелоперски."""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"order_{order_id}",
        {"type": "order.event", "data": payload},
    )
