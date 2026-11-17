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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "perfil"
        verbose_name_plural = "perfiles"

    def __str__(self) -> str:
        return self.house_name or self.user.get_username()
