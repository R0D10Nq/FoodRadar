from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.conf import settings

from apps.restaurants.models import Restaurant, Dish


class OrderStatus(models.TextChoices):
    CREATED = "created", "Создан (корзина)"
    PENDING_PAYMENT = "pending_payment", "Ожидает оплаты"
    PAID = "paid", "Оплачен"
    RESTAURANT_CONFIRMED = "restaurant_confirmed", "Ресторан подтвердил"
    READY_FOR_PICKUP = "ready_for_pickup", "Готов к выдаче"
    ACCEPTED = "accepted", "Курьер принял"
    IN_TRANSIT = "in_transit", "В пути"
    DELIVERED = "delivered", "Доставлен"
    CANCELED = "canceled", "Отменен"


class Order(models.Model):
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders", verbose_name="Клиент")
    restaurant = models.ForeignKey(Restaurant, on_delete=models.PROTECT, related_name="orders", verbose_name="Ресторан")
    courier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="deliveries", verbose_name="Курьер")

    status = models.CharField("Статус", max_length=32, choices=OrderStatus.choices, default=OrderStatus.CREATED)
    total = models.DecimalField("Сумма", max_digits=10, decimal_places=2, default=Decimal("0.00"))
    stripe_payment_intent_id = models.CharField("Stripe PaymentIntent", max_length=255, blank=True, default="")

    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлен", auto_now=True)

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ("-created_at",)

    def recalc_total(self) -> Decimal:
        """Пересчитываем сумму заказа по позициям. Возвращаем финальную сумму."""
        total = sum((item.qty * item.price_each for item in self.items.all()), start=Decimal("0.00"))
        self.total = total
        self.save(update_fields=["total"])
        return total


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items", verbose_name="Заказ")
    dish = models.ForeignKey(Dish, on_delete=models.PROTECT, related_name="order_items", verbose_name="Блюдо")
    qty = models.PositiveIntegerField("Количество", default=1)
    price_each = models.DecimalField("Цена за ед.", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказов"


class RatingFromRole(models.TextChoices):
    CLIENT = "client", "Клиент"
    COURIER = "courier", "Курьер"
    RESTAURANT = "restaurant", "Ресторан"


class Rating(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="ratings", verbose_name="Заказ")
    from_role = models.CharField("От кого", max_length=20, choices=RatingFromRole.choices)
    stars = models.PositiveSmallIntegerField("Звезды", default=5)
    comment = models.TextField("Комментарий", blank=True, default="")
    created_at = models.DateTimeField("Создан", auto_now_add=True)

    class Meta:
        verbose_name = "Оценка"
        verbose_name_plural = "Оценки"
