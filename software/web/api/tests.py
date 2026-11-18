import json
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from pets.models import Feeder, Pet
from telemetry.models import MealEvent

TOKEN = "dev-token"


@pytest.fixture
def feeder(db):
    User = get_user_model()
    user = User.objects.create_user(username="a@a.co", email="a@a.co", password="x")
    unit = Feeder.objects.create(owner=user, code="SPB-42", name="Cocina")
    Pet.objects.create(owner=user, name="Jiru", species="cat", weight_kg=10, feeder=unit, target_grams=131)
    return unit


@pytest.mark.django_db
def test_ingest_requires_token(client, feeder):
    response = client.post(reverse("api:ingest"), data="{}", content_type="application/json")
    assert response.status_code == 401


@pytest.mark.django_db
def test_ingest_stores_event(client, feeder):
    body = {
        "feeder": "SPB-42",
        "events": [{
            "uid": str(uuid.uuid4()), "pet": "Jiru",
            "scheduled_grams": 65, "served_grams": 64,
            "leftover_grams": 4, "eaten_grams": 60,
            "status": "ate", "confidence": 0.9,
        }],
    }
    response = client.post(
        reverse("api:ingest"), data=json.dumps(body), content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {TOKEN}",
    )
    assert response.status_code == 200
    assert MealEvent.objects.count() == 1


@pytest.mark.django_db
def test_ingest_is_idempotent(client, feeder):
    uid = str(uuid.uuid4())
    body = {"feeder": "SPB-42", "events": [{"uid": uid, "pet": "Jiru", "served_grams": 64, "eaten_grams": 60}]}
    for _ in range(3):
        client.post(
            reverse("api:ingest"), data=json.dumps(body), content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {TOKEN}",
        )
    assert MealEvent.objects.count() == 1


@pytest.mark.django_db
def test_ingest_rejects_unknown_feeder(client, feeder):
    body = {"feeder": "NO-EXISTE", "events": []}
    response = client.post(
        reverse("api:ingest"), data=json.dumps(body), content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {TOKEN}",
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_ingest_descarta_uid_invalido_sin_romper(client, feeder):
    """Un uid que no es UUID debe descartarse, no provocar un 500."""
    body = {
        "feeder": "SPB-42",
        "events": [
            {"uid": "Jiru-1763421234", "pet": "Jiru", "served_grams": 6, "eaten_grams": 0},
            {"uid": str(uuid.uuid4()), "pet": "Jiru", "served_grams": 65, "eaten_grams": 60, "status": "ate"},
        ],
    }
    response = client.post(
        reverse("api:ingest"), data=json.dumps(body), content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {TOKEN}",
    )
    assert response.status_code == 200
    assert response.json()["created"] == 1
    assert response.json()["skipped"] == 1
    assert MealEvent.objects.count() == 1
