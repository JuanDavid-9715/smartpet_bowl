from django.contrib import admin

from .models import Alert, MealEvent


@admin.register(MealEvent)
class MealEventAdmin(admin.ModelAdmin):
    list_display = ("pet", "occurred_at", "served_grams", "leftover_grams", "eaten_grams", "status", "synced")
    list_filter = ("status", "synced")
    search_fields = ("pet__name",)


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("title", "severity", "pet", "created_at", "read_at")
    list_filter = ("severity",)
