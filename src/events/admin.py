from django.contrib import admin

from .models import Event, Place


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ["name", "event_time", "status", "place"]
    list_filter = ["status", "event_time"]
    search_fields = ["name"]
    date_hierarchy = "event_time"
