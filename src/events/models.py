import uuid

from django.db import models


class Place(models.Model):
    """Площадка (место проведения события)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Площадка"
        verbose_name_plural = "Площадки"


class EventStatus(models.TextChoices):
    """Статусы мероприятия."""

    OPEN = "open", "Открыто"
    CLOSED = "closed", "Закрыто"


class Event(models.Model):
    """Мероприятие"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name="Название")
    event_time = models.DateTimeField(verbose_name="Дата проведения")
    status = models.CharField(
        max_length=10,
        choices=EventStatus.choices,
        default=EventStatus.OPEN,
        verbose_name="Статус",
    )
    place = models.ForeignKey(
        Place, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Площадка"
    )
    changed_at = models.DateTimeField(
        auto_now=True, verbose_name="Время последнего изменения"
    )
    registration_deadline = models.DateTimeField(
        verbose_name="Дедлайн регистрации", null=True, blank=True
    )

    def __str__(self):
        return f"{self.name} ({self.event_time})"

    class Meta:
        verbose_name = "Мероприятие"
        verbose_name_plural = "Мероприятия"
        ordering = ("event_time",)
        indexes = [
            # 1. Для главной страницы API (самый важный!)
            models.Index(fields=["status", "event_time"]),
            # 2. Для очистки старых мероприятий
            models.Index(fields=["event_time"]),
        ]


class Registration(models.Model):
    """Регистрация посетителя на мероприятие."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="registrations"
    )
    full_name = models.CharField(max_length=128)
    email = models.EmailField()
    confirmation_code = models.CharField(max_length=10, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Нельзя регистрироваться дважды на одно мероприятие
        unique_together = ["event", "email"]
        verbose_name = "Регистрация"
        verbose_name_plural = "Регистрации"

    def __str__(self):
        return f"{self.full_name} на {self.event.name}"


class OutboxMessage(models.Model):
    """Исходящие уведомления."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    registration = models.ForeignKey(
        "Registration", on_delete=models.CASCADE, related_name="outbox_messages"
    )
    payload = models.JSONField()  # {id, owner_id, email, message}
    created_at = models.DateTimeField(auto_now_add=True)
    sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Notification for {self.registration.email}"
