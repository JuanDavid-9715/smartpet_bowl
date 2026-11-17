"""Carga la cuenta demo y los datos de ejemplo.

La contrasena existe solo para la demostracion academica. En un despliegue real
se leería de una variable de entorno y no viviría en el repositorio.
"""
from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from pets.models import Feeder, MealTime, Pet
from telemetry.models import Alert, MealEvent

User = get_user_model()

PASSWORD = "Juan1234"


class Command(BaseCommand):
    help = "Crea la cuenta demo con Jiru y Armi, comederos e historial."

    def handle(self, *args, **options):
        email = settings.DEMO_EMAIL
        user, created = User.objects.get_or_create(
            username=email, defaults={"email": email, "first_name": "Juan David"}
        )
        user.email = email
        user.set_password(PASSWORD)
        user.save()
        if created:
            self.stdout.write(f"Cuenta creada: {email}")
        else:
            self.stdout.write(f"Cuenta actualizada: {email}")

        from accounts.models import Profile

        profile, _ = Profile.objects.get_or_create(user=user)
        profile.house_name = "Casa de los Medellin"
        profile.is_local_owner = True
        profile.save()

        feeder_cocina, _ = Feeder.objects.get_or_create(
            code="SPB-42", defaults={"owner": user, "name": "Cocina", "is_online": True}
        )
        feeder_patio, _ = Feeder.objects.get_or_create(
            code="SPB-07", defaults={"owner": user, "name": "Patio", "is_online": True}
        )
        Feeder.objects.get_or_create(
            code="SPB-19", defaults={"owner": user, "name": "Habitacion", "is_online": False}
        )
        for feeder in (feeder_cocina, feeder_patio):
            feeder.owner = user
            feeder.last_sync = timezone.now() - timedelta(minutes=2)
            feeder.save()

        hoy = timezone.localdate()
        jiru, _ = Pet.objects.get_or_create(
            owner=user, name="Jiru",
            defaults={
                "species": "cat",
                "breed": "Atigrado gris y blanco",
                "birth_date": date(hoy.year - 5, 5, 12),
                "weight_kg": 10,
                "kcal_per_gram": 3.6,
                "profile": "adult_neutered",
                "meals_per_day": 2,
                "feeder": feeder_cocina,
            },
        )
        armi, _ = Pet.objects.get_or_create(
            owner=user, name="Armi",
            defaults={
                "species": "dog",
                "breed": "Boxer",
                "birth_date": date(hoy.year - 2, 3, 8),
                "weight_kg": 31,
                "kcal_per_gram": 3.6,
                "profile": "adult_neutered",
                "meals_per_day": 2,
                "feeder": feeder_patio,
            },
        )
        for pet in (jiru, armi):
            ration = pet.suggested_ration()
            pet.target_grams = ration.grams_per_day
            pet.save()
            pet.meal_times.all().delete()
            pet.ensure_schedule()
            self.stdout.write(f"{pet.name}: {ration.grams_per_day} g al dia en {pet.meal_times.count()} comidas")

        if not MealEvent.objects.filter(pet=jiru).exists():
            plan = [
                (jiru, 0, 65, 65, 0, "ate", 0.93),
                (armi, 0, 217, 210, 7, "ate", 0.88),
                (jiru, 1, 65, 60, 5, "ate", 0.91),
                (armi, 1, 217, 210, 7, "ate", 0.9),
                (armi, 2, 217, 210, 7, "partial", 0.84),
                (jiru, 2, 65, 65, 20, "partial", 0.9),
                (armi, 3, 217, 210, 7, "ate", 0.87),
                (jiru, 3, 65, 40, 10, "none", 0.79),
            ]
            for pet, days_ago, served, eaten, leftover, status, confidence in plan:
                MealEvent.objects.create(
                    pet=pet,
                    feeder=pet.feeder,
                    occurred_at=timezone.now() - timedelta(days=days_ago, hours=pet.pk % 5),
                    scheduled_grams=served,
                    served_grams=served,
                    leftover_grams=leftover,
                    eaten_grams=eaten,
                    status=status,
                    confidence=confidence,
                    duration_seconds=90,
                    synced=not settings.IS_LOCAL,
                )

        if not Alert.objects.filter(pet=jiru).exists():
            Alert.objects.create(
                pet=jiru, feeder=feeder_cocina, severity="alert",
                title="Jiru dejo el 30% de su racion",
                detail="Sobrante alto en la ultima comida. Conviene revisar el plato.",
            )
            Alert.objects.create(
                feeder=feeder_patio, severity="resolved",
                title="El comedero SPB-07 se reconecto",
                detail="Estuvo fuera de linea 4 minutos y volvio solo.",
            )

        self.stdout.write(self.style.SUCCESS("Datos demo listos."))
