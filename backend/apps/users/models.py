"""
Модель пользователя с ролями. Логинимся по email.
"""
from __future__ import annotations

from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    BaseUserManager,
)


class UserRole(models.TextChoices):
    CLIENT = "client", "Клиент"
    RESTAURANT = "restaurant", "Ресторан"
    COURIER = "courier", "Курьер"
    ADMIN = "admin", "Админ"


class UserManager(BaseUserManager):
    """
    Свой менеджер — создаем юзеров по email, без username.
    """

    def _create_user(self, email: str, password: str | None, **extra_fields):
        if not email:
            raise ValueError("Email обязателен")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        if extra_fields.get("role") is None:
            extra_fields["role"] = UserRole.CLIENT
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", UserRole.ADMIN)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Суперпользователь должен иметь is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Суперпользователь должен иметь is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField("Email", unique=True)
    phone = models.CharField("Телефон", max_length=32, blank=True)
    role = models.CharField("Роль", max_length=20, choices=UserRole.choices, default=UserRole.CLIENT)

    is_active = models.BooleanField("Активен", default=True)
    is_staff = models.BooleanField("Сотрудник", default=False)
    date_joined = models.DateTimeField("Создан", auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self) -> str:  # pragma: no cover
        return self.email
