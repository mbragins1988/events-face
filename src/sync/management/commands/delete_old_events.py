from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from src.events.models import Event


class Command(BaseCommand):
    """uv run manage.py delete_old_events."""

    help = "Удаляет мероприятия, закончившиеся более 7 дней назад"

    def handle(self, *args, **options):
        delete_time = timezone.now() - timedelta(days=7)
        old_events = Event.objects.filter(event_time__lt=delete_time)

        count = old_events.count()
        old_events.delete()

        print(f"Удалено {count} мероприятий")
