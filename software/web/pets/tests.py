from datetime import date

import pytest
from django.contrib.auth import get_user_model

from pets import nutrition
from pets.models import MealTime, Pet


def test_rer_uses_metabolic_weight():
    assert nutrition.resting_energy(10) == pytest.approx(393.6, abs=0.5)


def test_ration_cat_10kg():
    ration = nutrition.compute_ration(species="cat", weight_kg=10)
    assert ration.grams_per_day == pytest.approx(131.3, abs=0.5)
    assert sum(ration.grams_per_meal) == pytest.approx(ration.grams_per_day, abs=0.1)


def test_ration_dog_31kg():
    ration = nutrition.compute_ration(species="dog", weight_kg=31)
    assert ration.grams_per_day == pytest.approx(408.3, abs=1.0)


def test_split_keeps_total():
    portions = nutrition.split_in_meals(131.2, 3)
    assert len(portions) == 3
    assert pytest.approx(sum(portions), abs=0.05) == 131.2


def test_leftover_reduces_next_portion():
    assert nutrition.adjust_for_leftover(65, 6.5) == pytest.approx(58.5)


def test_leftover_has_floor():
    assert nutrition.adjust_for_leftover(10, 9.5) == nutrition.MIN_GRAMS


@pytest.mark.parametrize("leftover,expected", [(0, "none"), (5, "none"), (20, "warning"), (50, "clean")])
def test_leftover_severity(leftover, expected):
    assert nutrition.leftover_severity(leftover, 100) == expected


@pytest.mark.django_db
def test_pet_suggests_ration_and_schedule():
    User = get_user_model()
    user = User.objects.create_user(username="t@t.co", email="t@t.co", password="x")
    pet = Pet.objects.create(
        owner=user, name="Jiru", species="cat", weight_kg=10,
        birth_date=date(2021, 5, 12), meals_per_day=2,
    )
    ration = pet.suggested_ration()
    assert ration.grams_per_day > 0
    pet.ensure_schedule()
    assert MealTime.objects.filter(pet=pet).count() == 2


@pytest.mark.django_db
def test_crear_mascota_con_plato_de_la_lista(client):
    from django.urls import reverse

    from pets.models import Feeder

    User = get_user_model()
    user = User.objects.create_user(username="p@p.co", email="p@p.co", password="x")
    plato = Feeder.objects.create(owner=user, code="SPB-11")
    client.force_login(user)
    response = client.post(reverse("pets:create"), {
        "name": "Nube", "species": "cat", "weight_kg": "4.5", "kcal_per_gram": "3.6",
        "profile": "adult_neutered", "meals_per_day": "2", "feeder": plato.pk,
    })
    assert response.status_code == 302
    assert Pet.objects.get(name="Nube").feeder_id == plato.pk


@pytest.mark.django_db
def test_crear_mascota_vinculando_plato_nuevo(client):
    from django.urls import reverse

    from pets.models import Feeder

    User = get_user_model()
    user = User.objects.create_user(username="q@q.co", email="q@q.co", password="x")
    client.force_login(user)
    response = client.post(reverse("pets:create"), {
        "name": "Trufa", "species": "dog", "weight_kg": "20", "kcal_per_gram": "3.6",
        "profile": "adult_neutered", "meals_per_day": "2", "new_feeder_code": "spb-99",
    })
    assert response.status_code == 302
    assert Feeder.objects.filter(code="SPB-99").exists()
    assert Pet.objects.get(name="Trufa").feeder.code == "SPB-99"


@pytest.mark.django_db
def test_formulario_exige_plato():
    from pets.forms import PetForm

    User = get_user_model()
    user = User.objects.create_user(username="r@r.co", email="r@r.co", password="x")
    form = PetForm(data={
        "name": "Sin", "species": "cat", "weight_kg": "4", "kcal_per_gram": "3.6",
        "profile": "adult_neutered", "meals_per_day": "2",
    }, user=user)
    assert not form.is_valid()
    assert "plato" in str(form.errors).lower()


@pytest.mark.django_db
def test_formulario_no_permite_dos_platos_a_la_vez():
    from pets.forms import PetForm
    from pets.models import Feeder

    User = get_user_model()
    user = User.objects.create_user(username="s@s.co", email="s@s.co", password="x")
    plato = Feeder.objects.create(owner=user, code="SPB-55")
    form = PetForm(data={
        "name": "Doble", "species": "cat", "weight_kg": "4", "kcal_per_gram": "3.6",
        "profile": "adult_neutered", "meals_per_day": "2",
        "feeder": plato.pk, "new_feeder_code": "SPB-56",
    }, user=user)
    assert not form.is_valid()


@pytest.mark.django_db
def test_desvincular_plato_desde_la_ficha(client):
    from django.urls import reverse

    from pets.models import Feeder

    User = get_user_model()
    user = User.objects.create_user(username="u@u.co", email="u@u.co", password="x")
    plato = Feeder.objects.create(owner=user, code="SPB-77", is_online=True)
    pet = Pet.objects.create(owner=user, name="Luna", species="cat", weight_kg=4, feeder=plato)
    client.force_login(user)

    response = client.post(reverse("pets:unassign_feeder", args=[pet.pk]))

    assert response.status_code == 302
    pet.refresh_from_db()
    assert pet.feeder is None
    assert Feeder.objects.filter(code="SPB-77").exists()


@pytest.mark.django_db
def test_archivar_libera_el_plato(client):
    from django.urls import reverse

    from pets.models import Feeder

    User = get_user_model()
    user = User.objects.create_user(username="v@v.co", email="v@v.co", password="x")
    plato = Feeder.objects.create(owner=user, code="SPB-31")
    pet = Pet.objects.create(owner=user, name="Onda", species="cat", weight_kg=4, feeder=plato)
    client.force_login(user)

    client.post(reverse("pets:archive", args=[pet.pk]))

    pet.refresh_from_db()
    assert pet.archived is True
    assert pet.feeder is None
    # El plato sigue existiendo y queda libre para otra mascota.
    libre = Feeder.objects.get(code="SPB-31")
    assert not libre.pets.exists()


@pytest.mark.django_db
def test_restaurar_mascota_archivada(client):
    from django.urls import reverse

    User = get_user_model()
    user = User.objects.create_user(username="w@w.co", email="w@w.co", password="x")
    pet = Pet.objects.create(owner=user, name="Nube", species="cat", weight_kg=4, archived=True)
    client.force_login(user)

    client.post(reverse("pets:restore", args=[pet.pk]))

    pet.refresh_from_db()
    assert pet.archived is False


@pytest.mark.django_db
def test_subir_fotos_calcula_vector(client, tmp_path, settings):
    import io

    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.urls import reverse
    from PIL import Image

    from pets import embedding
    from pets.models import PetPhoto

    settings.MEDIA_ROOT = tmp_path
    User = get_user_model()
    user = User.objects.create_user(username="f@f.co", email="f@f.co", password="x")
    pet = Pet.objects.create(owner=user, name="Foto", species="cat", weight_kg=4)
    client.force_login(user)

    def jpeg(color):
        buffer = io.BytesIO()
        Image.new("RGB", (64, 64), color).save(buffer, "JPEG")
        return SimpleUploadedFile("x.jpg", buffer.getvalue(), content_type="image/jpeg")

    response = client.post(reverse("pets:photos", args=[pet.pk]), {
        "front": jpeg((200, 120, 40)),
        "eating": jpeg((190, 110, 50)),
    })

    assert response.status_code == 302
    assert PetPhoto.objects.filter(pet=pet).count() == 2
    pet.refresh_from_db()
    assert len(pet.centroid) == embedding.DIMENSIONS


def test_vision_ida_y_vuelta():
    """Los puntos viajan como texto y deben volver identicos."""
    import numpy as np
    from pets import features as vision

    puntos = np.array([[i % 256] * 32 for i in range(5)], dtype=np.uint8)
    texto = vision.encode(puntos)
    vuelta = vision.decode(texto)
    assert vuelta is not None
    assert (vuelta == puntos).all()
    assert vision.decode("") is None
    assert vision.decode("basura") is None


def test_vision_compara():
    """La misma imagen coincide mucho mas consigo misma que con ruido."""
    import numpy as np
    from pets import features as vision

    rng = np.random.default_rng(7)
    a = rng.integers(0, 255, (40, 32), dtype=np.uint8)
    b = rng.integers(0, 255, (40, 32), dtype=np.uint8)
    assert vision.match_score(a, a) > vision.match_score(a, b)
    assert vision.combine([vision.encode(a), vision.encode(a)]) != ""
