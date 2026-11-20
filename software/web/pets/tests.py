from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

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
        "side": jpeg((190, 110, 50)),
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


@pytest.mark.django_db
@override_settings(IS_LOCAL=True)
def test_eventos_agrega_comida(client):
    from django.urls import reverse

    User = get_user_model()
    user = User.objects.create_user(username="e@e.co", email="e@e.co", password="x")
    pet = Pet.objects.create(owner=user, name="Jiru", species="cat", weight_kg=10,
                             meals_per_day=2, target_grams=131.2)
    client.force_login(user)
    response = client.post(reverse("pets:events"), {
        "accion": "agregar", "pet": pet.pk, "time": "06:45", "grams": "60",
    })
    assert response.status_code == 302
    comida = MealTime.objects.get(pet=pet, time="06:45")
    assert float(comida.grams) == 60.0


@pytest.mark.django_db
@override_settings(IS_LOCAL=True)
def test_eventos_gramos_automaticos(client):
    """Sin gramos usa la porcion sugerida de la racion diaria."""
    from django.urls import reverse

    User = get_user_model()
    user = User.objects.create_user(username="a@a.co", email="a@a.co", password="x")
    pet = Pet.objects.create(owner=user, name="Armi", species="dog", weight_kg=31,
                             meals_per_day=2, target_grams=204.3)
    client.force_login(user)
    client.post(reverse("pets:events"), {"accion": "agregar", "pet": pet.pk, "time": "19:30"})
    comida = MealTime.objects.get(pet=pet, time="19:30")
    assert float(comida.grams) == pytest.approx(102.2, abs=0.2)


@pytest.mark.django_db
@override_settings(IS_LOCAL=True)
def test_eventos_borra_comida(client):
    from django.urls import reverse

    User = get_user_model()
    user = User.objects.create_user(username="b@b.co", email="b@b.co", password="x")
    pet = Pet.objects.create(owner=user, name="Jiru", species="cat", weight_kg=10)
    comida = MealTime.objects.create(pet=pet, time="08:00", grams=50)
    client.force_login(user)
    client.post(reverse("pets:events"), {"accion": "borrar", "meal": comida.pk})
    assert not MealTime.objects.filter(pk=comida.pk).exists()


@pytest.mark.django_db
@override_settings(IS_LOCAL=True)
def test_eventos_no_toca_mascotas_ajenas(client):
    from django.urls import reverse

    User = get_user_model()
    dueno = User.objects.create_user(username="d@d.co", email="d@d.co", password="x")
    otro = User.objects.create_user(username="o@o.co", email="o@o.co", password="x")
    ajeno = Pet.objects.create(owner=otro, name="Ajena", species="cat", weight_kg=4)
    client.force_login(dueno)
    client.post(reverse("pets:events"), {"accion": "agregar", "pet": ajeno.pk, "time": "09:00"})
    assert MealTime.objects.filter(pet=ajeno).count() == 0


@pytest.mark.django_db
@override_settings(IS_LOCAL=True)
def test_eventos_envia_orden_al_comedero(client):
    from django.urls import reverse

    from pets.models import Feeder, FeederCommand

    User = get_user_model()
    user = User.objects.create_user(username="f@f.co", email="f@f.co", password="x")
    plato = Feeder.objects.create(owner=user, code="SPB-42")
    client.force_login(user)
    client.post(reverse("pets:events"), {
        "accion": "orden", "feeder": plato.pk, "action": "restart",
    })
    assert FeederCommand.objects.filter(feeder=plato, action="restart").exists()


@pytest.mark.django_db
@override_settings(IS_LOCAL=True)
def test_eventos_muestra_la_pagina(client):
    from django.urls import reverse

    User = get_user_model()
    user = User.objects.create_user(username="g@g.co", email="g@g.co", password="x")
    Pet.objects.create(owner=user, name="Jiru", species="cat", weight_kg=10)
    client.force_login(user)
    response = client.get(reverse("pets:events"))
    assert response.status_code == 200
    assert b"Agregar una comida" in response.content


@pytest.mark.django_db
@override_settings(IS_LOCAL=True)
def test_eventos_servir_ahora_va_al_equipo(client, monkeypatch):
    """Servir ahora habla directo con el ESP32, sin platos ni MQTT."""
    from django.urls import reverse

    from pets import views
    from pets.models import FeederCommand

    llamadas = []

    class Falsa:
        def raise_for_status(self):
            return None

        def json(self):
            return {}

    monkeypatch.setattr(views.requests, "post",
                        lambda url, **k: llamadas.append((url, k.get("json"))) or Falsa())

    User = get_user_model()
    user = User.objects.create_user(username="s@s.co", email="s@s.co", password="x")
    # Sin plato a proposito: el boton no debe depender de eso.
    pet = Pet.objects.create(owner=user, name="Jiru", species="cat", weight_kg=10,
                             meals_per_day=2, target_grams=131.2)
    client.force_login(user)
    client.post(reverse("pets:events"), {"accion": "servir", "pet": pet.pk})

    assert llamadas and llamadas[0][0].endswith("/api/dose")
    assert llamadas[0][1]["pet"] == "Jiru"
    assert llamadas[0][1]["grams"] == pytest.approx(65.6, abs=0.1)
    assert not FeederCommand.objects.exists()


@pytest.mark.django_db
@override_settings(IS_LOCAL=True)
def test_eventos_reinicia_el_equipo(client, monkeypatch):
    from django.urls import reverse

    from pets import views

    rutas = []

    class Falsa:
        def raise_for_status(self):
            return None

        def json(self):
            return {}

    monkeypatch.setattr(views.requests, "post",
                        lambda url, **k: rutas.append(url) or Falsa())
    User = get_user_model()
    user = User.objects.create_user(username="r@r.co", email="r@r.co", password="x")
    client.force_login(user)
    client.post(reverse("pets:events"), {"accion": "reset"})
    client.post(reverse("pets:events"), {"accion": "reboot"})
    assert any(r.endswith("/api/reset") for r in rutas)
    assert any(r.endswith("/api/reboot") for r in rutas)


@pytest.mark.django_db
@override_settings(IS_LOCAL=True)
def test_vivo_muestra_la_pagina(client, monkeypatch):
    from django.urls import reverse

    from pets import views

    class Falsa:
        def json(self):
            return {"cell_ok": True, "grams": 12.3, "raw": -1, "sensor_ok": True,
                    "distance": 120, "presence": False, "motor": False}

        def raise_for_status(self):
            return None

    monkeypatch.setattr(views._dispositivo_sesion, "get", lambda *a, **k: Falsa())
    User = get_user_model()
    user = User.objects.create_user(username="v@v.co", email="v@v.co", password="x")
    client.force_login(user)

    # la pantalla en vivo vive dentro de Eventos
    pagina = client.get(reverse("pets:events"))
    assert pagina.status_code == 200
    assert b"Peso en la celda" in pagina.content
    estado = client.get(reverse("pets:live_state"))
    assert estado.status_code == 200
    assert estado.json()["grams"] == 12.3
    # sin presencia no hay video
    assert client.get(reverse("pets:live_video")).status_code == 204


@pytest.mark.django_db
@override_settings(IS_LOCAL=True)
def test_vivo_sin_comedero_avisa(client, monkeypatch):
    import requests as requests_module
    from django.urls import reverse

    from pets import views

    def falla(*a, **k):
        raise requests_module.ConnectionError("sin red")

    monkeypatch.setattr(views._dispositivo_sesion, "get", falla)
    User = get_user_model()
    user = User.objects.create_user(username="w@w.co", email="w@w.co", password="x")
    client.force_login(user)
    respuesta = client.get(reverse("pets:live_state"))
    assert respuesta.status_code == 502
    assert respuesta.json()["online"] is False




@pytest.mark.django_db
@override_settings(IS_LOCAL=False)
def test_el_panel_tecnico_no_existe_en_la_nube(client):
    """En Render no hay ESP32: la pagina y su enlace no se publican."""
    from django.urls import reverse

    User = get_user_model()
    user = User.objects.create_user(username="n@n.co", email="n@n.co", password="x")
    client.force_login(user)

    assert client.get(reverse("pets:events")).status_code == 404
    assert client.get(reverse("pets:live_state")).status_code == 404
    assert client.get(reverse("pets:live_video")).status_code == 404

    ajustes = client.get(reverse("pets:settings"))
    assert ajustes.status_code == 200
    assert b"Panel tecnico" not in ajustes.content


def _jpeg_falso(color=(180, 120, 70)):
    """JPEG con textura: una imagen lisa no tiene puntos ORB que guardar."""
    import io
    import random

    from PIL import Image, ImageDraw

    imagen = Image.new("RGB", (320, 240), color)
    lapiz = ImageDraw.Draw(imagen)
    random.seed(11)
    for _ in range(60):
        x, y = random.randint(0, 300), random.randint(0, 220)
        r = random.randint(5, 18)
        lapiz.rectangle([x, y, x + r, y + r], fill=(random.randint(0, 255),
                                                    random.randint(0, 255),
                                                    random.randint(0, 255)))
    buffer = io.BytesIO()
    imagen.save(buffer, "JPEG")
    return buffer.getvalue()


@pytest.mark.django_db
@override_settings(IS_LOCAL=True)
def test_capturar_toma_guarda_la_foto_y_el_vector(client, monkeypatch):
    """El boton toma la foto desde la camara del plato, sin subir archivos."""
    from django.urls import reverse

    from pets import views
    from pets.models import PetPhoto

    class Respuesta:
        content = _jpeg_falso()

        def raise_for_status(self):
            return None

    monkeypatch.setattr(views._dispositivo_sesion, "get", lambda *a, **k: Respuesta())
    # La imagen sintetica no tiene animal: se simula que el detector lo ve.
    monkeypatch.setattr(views.features, "detecta_animal", lambda *a, **k: True)

    User = get_user_model()
    user = User.objects.create_user(username="c@c.co", email="c@c.co", password="x")
    pet = Pet.objects.create(owner=user, name="Jiru", species="cat", weight_kg=10)
    client.force_login(user)

    respuesta = client.post(reverse("pets:photo_capture", args=[pet.pk, "front"]))
    assert respuesta.status_code == 302

    foto = PetPhoto.objects.get(pet=pet, pose="front")
    assert foto.image.name.endswith(".jpg")
    assert len(foto.keypoints) > 0

    pet.refresh_from_db()
    assert pet.keypoints


@pytest.mark.django_db
@override_settings(IS_LOCAL=True)
def test_capturar_reemplaza_la_misma_toma(client, monkeypatch):
    from django.urls import reverse

    from pets import views
    from pets.models import PetPhoto

    class Respuesta:
        content = _jpeg_falso()

        def raise_for_status(self):
            return None

    monkeypatch.setattr(views._dispositivo_sesion, "get", lambda *a, **k: Respuesta())
    monkeypatch.setattr(views.features, "detecta_animal", lambda *a, **k: True)

    User = get_user_model()
    user = User.objects.create_user(username="d2@d.co", email="d2@d.co", password="x")
    pet = Pet.objects.create(owner=user, name="Armi", species="dog", weight_kg=31)
    client.force_login(user)

    client.post(reverse("pets:photo_capture", args=[pet.pk, "front"]))
    client.post(reverse("pets:photo_capture", args=[pet.pk, "front"]))
    client.post(reverse("pets:photo_capture", args=[pet.pk, "top"]))

    assert PetPhoto.objects.filter(pet=pet, pose="front").count() == 1
    assert pet.photos.count() == 2


@pytest.mark.django_db
@override_settings(IS_LOCAL=True)
def test_capturar_avisa_si_la_camara_no_responde(client, monkeypatch):
    import requests as requests_module
    from django.urls import reverse

    from pets import views

    def falla(*a, **k):
        raise requests_module.ConnectionError("sin camara")

    monkeypatch.setattr(views._dispositivo_sesion, "get", falla)
    User = get_user_model()
    user = User.objects.create_user(username="e2@e.co", email="e2@e.co", password="x")
    pet = Pet.objects.create(owner=user, name="Nube", species="cat", weight_kg=4)
    client.force_login(user)

    respuesta = client.post(reverse("pets:photo_capture", args=[pet.pk, "front"]))
    assert respuesta.status_code == 302
    assert pet.photos.count() == 0


@pytest.mark.django_db
@override_settings(IS_LOCAL=False)
def test_capturar_no_existe_en_la_nube(client):
    from django.urls import reverse

    User = get_user_model()
    user = User.objects.create_user(username="f2@f.co", email="f2@f.co", password="x")
    pet = Pet.objects.create(owner=user, name="Jiru", species="cat", weight_kg=10)
    client.force_login(user)

    assert client.get(reverse("pets:photo_preview", args=[pet.pk])).status_code == 404
    assert client.post(reverse("pets:photo_capture", args=[pet.pk, "front"])).status_code == 404


@pytest.mark.django_db
@override_settings(IS_LOCAL=True)
def test_capturar_rechaza_si_no_hay_animal(client, monkeypatch):
    """Una toma sin mascota no debe guardarse: ensuciaria el descriptor."""
    from django.urls import reverse

    from pets import views

    class Respuesta:
        content = _jpeg_falso()

        def raise_for_status(self):
            return None

    monkeypatch.setattr(views._dispositivo_sesion, "get", lambda *a, **k: Respuesta())
    monkeypatch.setattr(views.features, "detecta_animal", lambda *a, **k: False)

    User = get_user_model()
    user = User.objects.create_user(username="g2@g.co", email="g2@g.co", password="x")
    pet = Pet.objects.create(owner=user, name="Jiru", species="cat", weight_kg=10)
    client.force_login(user)

    respuesta = client.post(reverse("pets:photo_capture", args=[pet.pk, "front"]))
    assert respuesta.status_code == 302
    assert pet.photos.count() == 0
