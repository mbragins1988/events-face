from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from rest_framework import serializers

from src.events.models import Event, Place, Registration


class PlaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Place
        fields = ("id", "name")


class EventSerializer(serializers.ModelSerializer):
    """Сериализатор для мероприятий"""

    # Добавляем название площадки
    place_name = serializers.CharField(source="place.name", read_only=True)

    class Meta:
        model = Event
        fields = [
            "id",
            "name",
            "event_time",
            "status",
            "place_name",  # Показываем название площадки
            # "registration_deadline",
        ]


class RegistrationSerializer(serializers.ModelSerializer):
    """Сериализатор для регистрации на мероприятие."""

    class Meta:
        model = Registration
        fields = ["full_name", "email"]

    def validate_full_name(self, value):
        """Проверка имени (до 128 символов)."""

        if len(value) > 128:
            raise serializers.ValidationError("Имя не должно превышать 128 символов")
        return value

    def validate_email(self, value):
        try:
            validate_email(value)  # Встроенная проверка Django
            return value
        except ValidationError:
            raise serializers.ValidationError("Неверный формат email")

    def validate(self, data):
        """Дополнительные проверки."""

        # Получаем event_id из контекста
        event_id = self.context.get("event_id")

        if not event_id:
            raise serializers.ValidationError("Не указано мероприятие")

        # Проверяем существует ли мероприятие и открыто ли оно
        try:
            event = Event.objects.get(id=event_id, status="open")
        except Event.DoesNotExist:
            raise serializers.ValidationError(
                "Мероприятие не найдено или закрыто для регистрации"
            )

        # Проверяем нет ли уже регистрации
        if Registration.objects.filter(event=event, email=data["email"]).exists():
            raise serializers.ValidationError(
                "Вы уже зарегистрированы на это мероприятие"
            )

        return data
