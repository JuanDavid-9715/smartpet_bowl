from django import forms
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from . import nutrition

SPECIES_CHOICES = [("cat", "Gato"), ("dog", "Perro")]
PROFILE_CHOICES = [
    ("adult_neutered", "Adulto castrado"),
    ("adult_intact", "Adulto entero"),
    ("active", "Activo"),
    ("senior", "Senior"),
    ("weight_loss", "Control de peso"),
]


class Feeder(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="feeders")
    code = models.CharField("codigo", max_length=12, unique=True)
    name = models.CharField("nombre", max_length=60, blank=True)
    is_online = models.BooleanField("en linea", default=False)
    last_sync = models.DateTimeField("ultima sincronizacion", null=True, blank=True)
    firmware = models.CharField("firmware", max_length=40, blank=True)

    class Meta:
        verbose_name = "comedero"
        verbose_name_plural = "comederos"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} · {self.name}" if self.name else self.code

    @property
    def status_label(self) -> str:
        return "En linea" if self.is_online else "Sin conexion"

    @property
    def last_sync_label(self) -> str:
        if not self.last_sync:
            return "Nunca"
        delta = timezone.now() - self.last_sync
        minutes = int(delta.total_seconds() // 60)
        if minutes < 1:
            return "Hace unos segundos"
        if minutes < 60:
            return f"Hace {minutes} min"
        hours = minutes // 60
        if hours < 24:
            return f"Hace {hours} h"
        return f"Hace {hours // 24} dias"


class Pet(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pets")
    name = models.CharField("nombre", max_length=60)
    species = models.CharField("especie", max_length=8, choices=SPECIES_CHOICES, default="cat")
    breed = models.CharField("raza", max_length=80, blank=True)
    birth_date = models.DateField("nacimiento", null=True, blank=True)
    weight_kg = models.DecimalField("peso (kg)", max_digits=5, decimal_places=2, default=4)
    kcal_per_gram = models.DecimalField(
        "kcal por gramo del alimento", max_digits=4, decimal_places=2, default=3.6,
        help_text="Esta impreso en la bolsa del pienso. Sin este dato la racion es una suposicion.",
    )
    profile = models.CharField("perfil", max_length=20, choices=PROFILE_CHOICES, default="adult_neutered")
    meals_per_day = models.PositiveSmallIntegerField("comidas al dia", default=2)
    feeder = models.ForeignKey(
        Feeder, on_delete=models.SET_NULL, null=True, blank=True, related_name="pets",
        verbose_name="comedero asignado",
    )
    photo = models.ImageField("foto", upload_to="pets/", blank=True)
    archived = models.BooleanField("archivada", default=False)
    keypoints = models.TextField(
        "puntos caracteristicos", blank=True, default="",
        help_text="Descriptores ORB de las fotos de referencia, juntos.",
    )
    centroid = models.JSONField(
        "vector de reconocimiento", default=list, blank=True,
        help_text="Promedio de los vectores de sus fotos. La Raspberry compara contra esto.",
    )
    target_grams = models.DecimalField("racion diaria (g)", max_digits=6, decimal_places=1, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "mascota"
        verbose_name_plural = "mascotas"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["feeder"],
                condition=Q(feeder__isnull=False),
                name="uniq_pet_per_feeder",
                violation_error_message="Ese plato ya tiene una mascota asignada.",
            )
        ]

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self):
        return reverse("pets:detail", args=[self.pk])

    @property
    def is_cat(self) -> bool:
        return self.species == "cat"

    @property
    def species_label(self) -> str:
        return "Gata" if self.is_cat else "Perro"

    @property
    def age_years(self):
        if not self.birth_date:
            return None
        today = timezone.localdate()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )

    def suggested_ration(self) -> nutrition.Ration:
        return nutrition.compute_ration(
            species=self.species,
            weight_kg=float(self.weight_kg),
            kcal_per_gram=float(self.kcal_per_gram),
            profile=self.profile,
            meals=self.meals_per_day or 2,
        )

    def ensure_schedule(self) -> None:
        """Crea los horarios por defecto segun la especie si no existen."""
        if self.meal_times.exists():
            return
        defaults = ["07:30", "19:30"] if self.is_cat else ["08:00", "20:00"]
        ration = self.suggested_ration()
        for index, portion in enumerate(ration.grams_per_meal[: len(defaults)]):
            MealTime.objects.create(pet=self, time=defaults[index], grams=portion)


class MealTime(models.Model):
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name="meal_times")
    time = models.TimeField("hora")
    grams = models.DecimalField("gramos", max_digits=6, decimal_places=1)

    class Meta:
        verbose_name = "horario de comida"
        verbose_name_plural = "horarios de comida"
        ordering = ["time"]

    def __str__(self) -> str:
        return f"{self.pet.name} {self.time:%H:%M} · {self.grams} g"


class MealPlanItem(models.Model):
    """Porcion sugerida por el sistema frente a la que la persona decide."""

    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name="plan_items")
    label = models.CharField(max_length=40)
    suggested_grams = models.DecimalField(max_digits=6, decimal_places=1)
    chosen_grams = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    time = models.TimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.pet.name} · {self.label}"

    @property
    def effective_grams(self):
        return self.chosen_grams if self.chosen_grams is not None else self.suggested_grams


class PetPhoto(models.Model):
    """Foto de referencia para que el sistema reconozca a la mascota."""

    POSES = [
        ("front", "Frente al plato"),
        ("side", "De perfil"),
        ("top", "Desde arriba"),
    ]

    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="pets/reference/")
    pose = models.CharField("toma", max_length=10, choices=POSES, default="front")
    keypoints = models.TextField("puntos caracteristicos", blank=True, default="")
    embedding = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "foto de referencia"
        verbose_name_plural = "fotos de referencia"
        ordering = ["pose"]

    def __str__(self) -> str:
        return f"{self.pet.name} · {self.get_pose_display()}"


class FeederCommand(models.Model):
    """Orden pendiente para un comedero. La Raspberry las recoge y las publica."""

    ACTIONS = [
        ("reconnect", "Reconectar"),
        ("restart", "Reiniciar"),
        ("feed", "Servir ahora"),
    ]

    feeder = models.ForeignKey(Feeder, on_delete=models.CASCADE, related_name="commands")
    action = models.CharField(max_length=12, choices=ACTIONS, default="reconnect")
    target = models.CharField("mascota", max_length=60, blank=True, default="")
    grams = models.DecimalField("gramos", max_digits=6, decimal_places=1, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "orden de comedero"
        verbose_name_plural = "ordenes de comedero"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.feeder.code} · {self.get_action_display()}"


class FeederAddForm(forms.Form):
    code = forms.CharField(label="Codigo del plato", max_length=12)
