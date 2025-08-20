from __future__ import annotations

from decimal import Decimal
import uuid
import factory
from factory.django import DjangoModelFactory

from apps.users.models import User, UserRole
from apps.restaurants.models import Restaurant, Dish
from apps.orders.models import Order, OrderItem
from apps.courier.models import CourierLocation


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    # Уникальный email: общий counter + uuid, чтобы не пересекались с подклассами фабрики
    email = factory.Sequence(lambda n: f"user{n}-{uuid.uuid4().hex}@example.com")
    role = UserRole.CLIENT
    is_active = True


class CourierFactory(UserFactory):
    role = UserRole.COURIER


class RestaurantFactory(DjangoModelFactory):
    class Meta:
        model = Restaurant

    owner = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f"Resto {n}")
    address = factory.Faker("address")
    lat = 55.75
    lon = 37.61


class DishFactory(DjangoModelFactory):
    class Meta:
        model = Dish

    restaurant = factory.SubFactory(RestaurantFactory)
    name = factory.Sequence(lambda n: f"Dish {n}")
    price = Decimal("10.00")
    allergens = []
    is_available = True


class OrderFactory(DjangoModelFactory):
    class Meta:
        model = Order

    client = factory.SubFactory(UserFactory)
    restaurant = factory.SubFactory(RestaurantFactory)
    status = "created"
    total = Decimal("20.00")


class OrderItemFactory(DjangoModelFactory):
    class Meta:
        model = OrderItem

    order = factory.SubFactory(OrderFactory)
    dish = factory.SubFactory(DishFactory)
    qty = 1
    price_each = Decimal("10.00")


class CourierLocationFactory(DjangoModelFactory):
    class Meta:
        model = CourierLocation

    courier = factory.SubFactory(CourierFactory)
    lat = 55.75
    lon = 37.61
