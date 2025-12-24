from django.db import models


class SyncResult(models.Model):
    """Результаты синхронизации."""

    sync_date = models.DateTimeField(
        auto_now_add=True, verbose_name="Дата и время синхронизации"
    )
    added_count = models.IntegerField(default=0, verbose_name="Добавлено мероприятий")
    updated_count = models.IntegerField(default=0, verbose_name="Обновлено мероприятий")

    class Meta:
        verbose_name = "Результат синхронизации"
        verbose_name_plural = "Результаты синхронизаций"
        ordering = ["-sync_date"]

    def __str__(self):
        return f"Результат синхронизации {self.sync_date}"
