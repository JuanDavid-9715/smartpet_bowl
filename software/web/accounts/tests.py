import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from pets.models import Feeder, Pet


@pytest.mark.django_db
def test_registro_crea_cuenta_vacia(client):
    """Una cuenta nueva tiene que entrar sin mascotas, platos ni historial."""
    data = {
        "username": "nueva@correo.com",
        "email": "nueva@correo.com",
        "password1": "ClaveSegura2026",
        "password2": "ClaveSegura2026",
    }
    response = client.post(reverse("accounts:register"), data)
    assert response.status_code == 302

    User = get_user_model()
    user = User.objects.get(email="nueva@correo.com")
    assert Pet.objects.filter(owner=user).count() == 0
    assert Feeder.objects.filter(owner=user).count() == 0
    assert user.profile.plan == "hogar"

    panel = client.get(reverse("pets:dashboard"))
    assert panel.status_code == 200
    assert b"Todavia no hay mascotas" in panel.content
