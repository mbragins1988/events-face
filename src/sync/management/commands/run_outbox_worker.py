# management/commands/run_outbox_worker.py
import signal
import sys

from django.core.management.base import BaseCommand

from src.events.views import process_outbox


class Command(BaseCommand):
    """uv run run_outbox_worker."""

    help = "Запускает воркер для обработки outbox сообщений"

    def handle(self, *args, **options):
        print("Запуск outbox воркера")

        # Обработка Ctrl+C
        def signal_handler(sig, frame):
            self.stdout.write(self.style.WARNING("Остановка воркера"))
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)

        # Запускаем бесконечный цикл
        process_outbox()
