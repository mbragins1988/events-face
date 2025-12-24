import json
import secrets
import time
import uuid
from datetime import timezone
from venv import logger

import requests
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from kafka import KafkaProducer
from rest_framework import filters, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from src.core.settings import NOTIFICATIONS_API_TOKEN, NOTIFICATIONS_OWNER_ID
from src.events.models import Event, Registration
from src.events.serializers import EventSerializer, RegistrationSerializer

from .models import OutboxMessage


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
        # Генерируем уникальный ID для уведомления
        notification_id = uuid.uuid4()

        # В одной транзакции
        with transaction.atomic():
            # Создаём регистрацию пользователя на мероприятие
            registration = Registration.objects.create(
                event=event,
                full_name=serializer.validated_data["full_name"],
                email=serializer.validated_data["email"],
                confirmation_code=confirmation_code,
            )

            # Сохраняем в outbox
            message = OutboxMessage.objects.create(
                registration=registration,
                payload={
                    "id": str(notification_id),  # УНИКАЛЬНЫЙ для каждого уведомления
                    "owner_id": str(NOTIFICATIONS_OWNER_ID),
                    "email": registration.email,
                    "message": f"Здравствуйте, {registration.full_name}!\nВы успешно зарегистрировались на мероприятие: {event.name}.\nВаш код подтверждения: {confirmation_code}",
                },
            )

        url = "https://notifications.k3scluster.tech/api/notifications"

        headers = {
            "Authorization": str(NOTIFICATIONS_API_TOKEN),
            "Content-Type": "application/json",
        }
        try:
            response = requests.post(url, json=message.payload, headers=headers)
            response.raise_for_status()
            message.sent = True
            message.sent_at = timezone.now()
            message.save()
            return Response(
                {"message": "Регистрация успешно завершена!"},
                status=status.HTTP_201_CREATED,
            )

        except Exception:
            return Response(response, status=status.HTTP_400_BAD_REQUEST)


# worker.py
def process_outbox():
    while True:
        with transaction.atomic():
            # Получаем неотправленные сообщения
            messages = (
                OutboxMessage.objects.filter(sent=False)
                .select_for_update(skip_locked=True)
                .order_by("created_at")[:100]
            )

            for message in messages:
                try:
                    # Создание продюсера
                    producer = KafkaProducer(
                        bootstrap_servers=["localhost:9092"],  # адрес Kafka-брокера
                        value_serializer=lambda v: json.dumps(v).encode(
                            "utf-8"
                        ),  # сериализатор JSON
                    )
                    # Отправляем в Kafka/RabbitMQ/etc
                    producer.send(
                        "notifications_topic",
                        value={
                            "id": message.id,
                            "owner_id": message.owner_id,
                            "email": message.email,
                            "message": message.message,
                        },
                    )

                    # Помечаем как отправленное
                    message.sent = True
                    message.sent_at = timezone.now()
                    message.save()
                except Exception as e:
                    logger.error(f"Failed to process message {message.id}: {e}")

        time.sleep(1)  # Пауза между итерациями
