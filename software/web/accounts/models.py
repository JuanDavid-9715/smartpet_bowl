from django.conf import settings
from django.db import models


class Profile(models.Model):
    """Datos del hogar. En modo local identifica el perfil unico de la casa."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    house_name = models.CharField("nombre de la casa", max_length=120, blank=True)
    is_local_owner = models.BooleanField(
        "perfil local", default=False,
        help_text="Marca el perfil que usa la Raspberry cuando no hay inicio de sesion.",
    )
    PLAN_CHOICES = [("hogar", "Hogar"), ("multi", "Multi"), ("local", "Local")]
    plan = models.CharField("plan", max_length=10, choices=PLAN_CHOICES, default="hogar")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "perfil"
        verbose_name_plural = "perfiles"

    # Cuantos platos permite el plan. None significa sin limite.
    PLAN_PLATES = {"hogar": 1, "multi": 4, "local": None}

    @property
    def max_plates(self) -> int | None:
        from django.conf import settings

        if settings.IS_LOCAL:
            return None
        return self.PLAN_PLATES.get(self.plan, 1)

    def __str__(self) -> str:
        return self.house_name or self.user.get_username()
