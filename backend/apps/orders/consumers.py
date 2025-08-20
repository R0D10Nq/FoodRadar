from __future__ import annotations

from channels.generic.websocket import AsyncJsonWebsocketConsumer


class OrderTrackerConsumer(AsyncJsonWebsocketConsumer):
    """Примитивный консюмер — просто вступает в группу заказа и ретрансмитит события."""

    async def connect(self):
        # path: /ws/track/<order_id>
        try:
            order_id = self.scope["url_route"]["kwargs"]["order_id"]
        except Exception:
            await self.close(code=4001)
            return
        self.group_name = f"order_{order_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):  # noqa: ARG002
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def order_event(self, event):
        # event должен содержать ключ "data"
        await self.send_json(event.get("data", {}))
