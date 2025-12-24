import secrets

import requests
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from src.core.settings import NOTIFICATIONS_API_TOKEN, NOTIFICATIONS_OWNER_ID
from src.events.models import Event, Registration
from src.events.serializers import EventSerializer, RegistrationSerializer


class EventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Эндпоинт для получения списка мероприятий.
    /api/events
    Фильтрация по названию: ?name=концерт
    Сортировка по дате: ?ordering=event_time (по возрастанию)
    Сортировка по дате (обратная): ?ordering=-event_time
    """

    # Берем только открытые мероприятия
    # Используем select_related чтобы избежать N+1 проблемы
    queryset = Event.objects.filter(status="open").select_related("place")
    serializer_class = EventSerializer
    # Добавляем фильтрацию и сортировку
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["name", "status", "registration_deadline"]
    ordering_fields = ["event_time"]  # Сортировка по дате
    ordering = ["event_time"]  # По умолчанию сортируем по дате


class EventRegisterView(APIView):
    """Регистрации на мероприятие."""

    def post(self, request, event_id):
        """
        POST /api/events/<event_id>/register/

        Пример запроса:
        {
            "full_name": "Иван Иванов",
            "email": "ivanov@mail.com"
        }
        """
        # Проверяем что мероприятие существует и открыто
        try:
            event = Event.objects.get(id=event_id, status="open")
        except Event.DoesNotExist:
            return Response(
                {"error": "Мероприятие не найдено или закрыто для регистрации"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Валидируем входные данные
        serializer = RegistrationSerializer(
            data=request.data,
            context={"event_id": event_id},  # Передаём event_id для валидации
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Генерируем код подтверждения
        confirmation_code = secrets.token_hex(3).upper()

        # Создаем регистрацию пользователя на мероприятие
        registration = Registration.objects.create(
            event=event,
            full_name=serializer.validated_data["full_name"],
            email=serializer.validated_data["email"],
            confirmation_code=confirmation_code,  # Сохраняем код в базу
        )

        url = "https://notifications.k3scluster.tech/api/notifications"

        payload = {
            "id": str(event_id),
            "owner_id": str(NOTIFICATIONS_OWNER_ID),
            "email": str(registration.email),
            "message": f"Здравствуйте, {registration.full_name}!\nВы успешно зарегистрировались на мероприятие: {event.name}.\nВаш код подтверждения: {confirmation_code}",
        }
        headers = {
            "Authorization": f"Bearer {NOTIFICATIONS_API_TOKEN}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                return Response(
                    {
                        "message": "Регистрация успешно завершена!",
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                print(f"{response} - Сообщение не отправлено")
                return Response(response, status=status.HTTP_403_FORBIDDEN)

        except Exception:
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
