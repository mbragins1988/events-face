import requests
from django.core.management.base import BaseCommand

from src.core.settings import NOTIFICATIONS_API_TOKEN
from src.events.models import Event, Place


class Command(BaseCommand):
    """Примеры команд
    uv run manage.py sync_events - обычная синхронизация
    uv run manage.py sync_events --all - полная синхронизация
    uv run manage.py sync_events --date 2024-01-20 - синхронизация по дате."""

    help = "Синхронизирует мероприятия"

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true", help="Полная синхронизация")
        parser.add_argument("--date", type=str, help="Дата для синхронизации")

    def handle(self, *args, **options):
        headers = {
            "Authorization": NOTIFICATIONS_API_TOKEN,
            "Content-Type": "application/json",
        }
        # Печатаем сообщение начала команды
        print("Начало синхронизации.")

        # URL внешнего API
        url = "https://events.k3scluster.tech/api/events/"

        try:
            # Делаем запрос к внешнему API
            response = requests.get(url, headers=headers)

            # Преобразуем ответ в JSON
            events = response.json()
            added = 0
            updated = 0

            # 3. Для каждого мероприятия в ответе
            for event in events.get("results"):
                # Создаем или находим площадку
                place = None
                # Если есть информация о площадке
                if event.get("place"):
                    place, _ = Place.objects.get_or_create(
                        id=event["place"]["id"],
                        defaults={"name": event["place"]["name"]},
                    )

                # Создаем или обновляем мероприятие
                _, created = Event.objects.update_or_create(
                    id=event["id"],
                    defaults={
                        "name": event["name"],
                        "event_time": event["event_time"],
                        "status": event["status"],
                        "place": place,
                    },
                )
                if created:
                    added += 1
                else:
                    updated += 1

            # 4. Показываем результат
            self.stdout.write(f"Готово! Добавлено: {added}, Обновлено: {updated}")

        except Exception as e:
            # Если ошибка
            self.stdout.write(f"Ошибка: {e}")
