import pytest
from django.test import override_settings
from django.urls import reverse


@pytest.mark.django_db
@override_settings(IS_LOCAL=True)
def test_en_local_la_raiz_lleva_a_la_app(client):
    """La Raspberry no sirve la landing: entra directo al panel."""
    response = client.get("/")
    assert response.status_code == 302
    assert response["Location"] == reverse("pets:dashboard")


@pytest.mark.django_db
@override_settings(IS_LOCAL=True)
def test_en_local_las_paginas_publicas_no_existen(client):
    for name in ("core:product", "core:plans", "core:open_source", "core:checkout"):
        response = client.get(reverse(name))
        assert response.status_code == 302, name


@pytest.mark.django_db
@override_settings(IS_LOCAL=False)
def test_en_la_nube_la_raiz_muestra_la_landing(client):
    response = client.get("/")
    assert response.status_code == 200
