from __future__ import annotations

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.request import Request

from .serializers import RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    """
    Регистрация пользователя. По умолчанию роль — клиент.
    Возвращаем данные пользователя без токенов (токен — отдельной ручкой).
    """
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request: Request, *args, **kwargs):
        # Своя реализация, чтобы вернуть нормальные поля пользователя
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        data = UserSerializer(user).data
        headers = self.get_success_headers(serializer.data)
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)

    def get_queryset(self):  # для mypy/DRF generic
        from django.contrib.auth import get_user_model
        return get_user_model().objects.all()
