from __future__ import annotations

from rest_framework import serializers

from .models import Restaurant, Dish


class RestaurantListSerializer(serializers.ModelSerializer):
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = Restaurant
        fields = ("id", "name", "address", "lat", "lon", "distance_km")

    def get_distance_km(self, obj) -> float | None:  # noqa: ANN001
        d = getattr(obj, "distance", None)
        if d is None:
            return None
        try:
            return round(d.km, 3)
        except Exception:  # на всякий случай, если бэкенд вернул метры как float
            try:
                return round(float(d) / 1000.0, 3)
            except Exception:  # pragma: no cover
                return None


class DishSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dish
        fields = ("id", "name", "price", "allergens", "is_available")


class RestaurantMenuSerializer(serializers.ModelSerializer):
    dishes = DishSerializer(many=True)

    class Meta:
        model = Restaurant
        fields = ("id", "name", "address", "lat", "lon", "dishes")
