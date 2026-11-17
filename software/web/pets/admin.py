from django.contrib import admin

from .models import Feeder, MealTime, Pet


@admin.register(Feeder)
class FeederAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_online", "last_sync")
    search_fields = ("code", "name")


class MealTimeInline(admin.TabularInline):
    model = MealTime
    extra = 0


@admin.register(Pet)
class PetAdmin(admin.ModelAdmin):
    list_display = ("name", "species", "weight_kg", "target_grams", "feeder", "archived")
    list_filter = ("species", "archived")
    inlines = [MealTimeInline]
