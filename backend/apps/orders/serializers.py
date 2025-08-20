from __future__ import annotations

from decimal import Decimal
from typing import List

from rest_framework import serializers

from apps.restaurants.models import Dish, Restaurant
from .models import Order, OrderItem, OrderStatus


class OrderItemCreateSerializer(serializers.Serializer):
    dish_id = serializers.IntegerField()
    qty = serializers.IntegerField(min_value=1)


class OrderCreateSerializer(serializers.Serializer):
    restaurant_id = serializers.IntegerField()
    items = OrderItemCreateSerializer(many=True)

    def validate(self, attrs):
        # Простейшие валидации: ресторан существует и активен, блюда — доступны
        restaurant_id = attrs.get("restaurant_id")
        items: List[dict] = attrs.get("items", [])
        try:
            restaurant = Restaurant.objects.get(pk=restaurant_id, is_active=True)
        except Restaurant.DoesNotExist:
            raise serializers.ValidationError({"restaurant_id": "Ресторан не найден или неактивен."})
        if not items:
            raise serializers.ValidationError({"items": "Позиции заказа пустые."})

        dish_ids = [i["dish_id"] for i in items]
        dishes = {d.id: d for d in Dish.objects.filter(id__in=dish_ids, restaurant=restaurant, is_available=True)}
        for it in items:
            if it["dish_id"] not in dishes:
                raise serializers.ValidationError({"items": f"Блюдо {it['dish_id']} недоступно"})
        attrs["restaurant"] = restaurant
        attrs["dishes_map"] = dishes
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        user = request.user
        restaurant = validated_data["restaurant"]
        dishes_map: dict[int, Dish] = validated_data["dishes_map"]
        items: List[dict] = validated_data["items"]

        order = Order.objects.create(
            client=user,
            restaurant=restaurant,
            status=OrderStatus.CREATED,
        )
        bulk_items = []
        for it in items:
            dish = dishes_map[it["dish_id"]]
            qty = int(it["qty"]) or 1
            bulk_items.append(OrderItem(order=order, dish=dish, qty=qty, price_each=dish.price))
        OrderItem.objects.bulk_create(bulk_items)
        order.recalc_total()
        return order


class OrderItemSerializer(serializers.ModelSerializer):
    dish_name = serializers.CharField(source="dish.name", read_only=True)

    class Meta:
        model = OrderItem
        fields = ("id", "dish", "dish_name", "qty", "price_each")


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "client",
            "restaurant",
            "courier",
            "status",
            "total",
            "stripe_payment_intent_id",
            "created_at",
            "updated_at",
            "items",
        )
        read_only_fields = ("id", "client", "created_at", "updated_at", "stripe_payment_intent_id", "total")


class OrderStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=OrderStatus.choices)
