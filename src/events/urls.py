from django.urls import path
from rest_framework.routers import DefaultRouter

from src.events.views import EventRegisterView, EventViewSet

urlpatterns = [
    path(
        "<uuid:event_id>/register/", EventRegisterView.as_view(), name="event-register"
    ),
]

router = DefaultRouter()
router.register(r"", EventViewSet, basename="events")  # Регистрируем по корню

# Добавляем маршруты роутера В КОНЕЦ
urlpatterns += router.urls
