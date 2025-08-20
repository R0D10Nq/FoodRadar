from __future__ import annotations

from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import CourierLocation

User = get_user_model()


class CourierLocationSerializer(serializers.ModelSerializer):
    lat = serializers.FloatField()
    lon = serializers.FloatField()

    class Meta:
        model = CourierLocation
        fields = ("id", "lat", "lon", "ts")
        read_only_fields = ("id", "ts")

    def create(self, validated_data):
        user: User = self.context["request"].user
        return CourierLocation.objects.create(courier=user, **validated_data)
