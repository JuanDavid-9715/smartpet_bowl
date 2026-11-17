import uuid

from django.db import models

from pets.models import Feeder, Pet


class MealEvent(models.Model):
    """Una comida registrada por el comedero y procesada por la Raspberry."""

    STATUS_CHOICES = [("ate", "Comio"), ("partial", "Comio parte"), ("none", "No comio")]

    event_uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name="events")
    feeder = models.ForeignKey(Feeder, on_delete=models.SET_NULL, null=True, blank=True, related_name="events")
    occurred_at = models.DateTimeField()
    scheduled_grams = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    served_grams = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    leftover_grams = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    eaten_grams = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="ate")
    confidence = models.FloatField(default=0)
    duration_seconds = models.PositiveIntegerField(default=0)
    synced = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "comida"
        verbose_name_plural = "comidas"
        ordering = ["-occurred_at"]
        indexes = [models.Index(fields=["pet", "-occurred_at"])]

    def __str__(self) -> str:
        return f"{self.pet.name} {self.occurred_at:%d %b %H:%M} · {self.served_grams} g"

    @property
    def compliance(self) -> int:
        if not self.served_grams:
            return 0
        return round(float(self.eaten_grams) / float(self.served_grams) * 100)


class Alert(models.Model):
    SEVERITY_CHOICES = [
        ("alert", "Alerta"),
        ("warning", "Aviso"),
        ("resolved", "Resuelto"),
    ]

    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, null=True, blank=True, related_name="alerts")
    feeder = models.ForeignKey(Feeder, on_delete=models.SET_NULL, null=True, blank=True, related_name="alerts")
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default="warning")
    title = models.CharField(max_length=140)
    detail = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "alerta"
        verbose_name_plural = "alertas"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title

    @property
    def is_unread(self) -> bool:
        return self.read_at is None
