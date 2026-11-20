from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Sum
import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.http import Http404, HttpResponse, JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from telemetry.models import Alert, MealEvent

from . import nutrition
from .forms import PetForm, PetPhotoForm
from . import embedding, features
from .models import Feeder, FeederCommand, MealTime, Pet, PetPhoto


def _pets(request):
    return Pet.objects.filter(owner=request.user, archived=False).select_related("feeder")


@login_required
def dashboard(request):
    today = timezone.localdate()
    pets = list(_pets(request))
    events_today = MealEvent.objects.filter(pet__in=pets, occurred_at__date=today)
    served = events_today.aggregate(total=Sum("served_grams"))["total"] or 0
    eaten = events_today.aggregate(total=Sum("eaten_grams"))["total"] or 0
    planned = sum(float(p.target_grams or 0) for p in pets)

    per_pet = []
    for pet in pets:
        pet_events = events_today.filter(pet=pet)
        pet_served = pet_events.aggregate(total=Sum("served_grams"))["total"] or 0
        target = float(pet.target_grams or 0)
        per_pet.append({
            "pet": pet,
            "served": pet_served,
            "target": target,
            "percent": round(float(pet_served) / target * 100) if target else 0,
        })

    feeders = Feeder.objects.filter(owner=request.user)
    return render(request, "pets/dashboard.html", {
        "pets": per_pet,
        "served": served,
        "eaten": eaten,
        "planned": planned,
        "percent": round(float(served) / planned * 100) if planned else 0,
        "events": events_today.select_related("pet")[:4],
        "feeders": feeders,
        "today": today,
    })


@login_required
def pet_list(request):
    pets = list(_pets(request))
    limit = _capacity(request)
    return render(request, "pets/pet_list.html", {
        "pets": pets,
        "limit": limit,
        "used": len(pets),
        "can_add": limit is None or len(pets) < limit,
    })


@login_required
def pet_detail(request, pk):
    pet = get_object_or_404(_pets(request), pk=pk)
    today = timezone.localdate()
    events = pet.events.filter(occurred_at__date=today)[:4]
    served = pet.events.filter(occurred_at__date=today).aggregate(t=Sum("served_grams"))["t"] or 0
    target = float(pet.target_grams or 0)
    return render(request, "pets/pet_detail.html", {
        "pet": pet,
        "events": events,
        "served": served,
        "percent": round(float(served) / target * 100) if target else 0,
        "ration": pet.suggested_ration(),
        "feeders": Feeder.objects.filter(owner=request.user),
    })


def _capacity(request):
    """Cuantas mascotas permite el plan. None = sin limite."""
    return getattr(request.user.profile, "max_plates", None)


@login_required
def pet_create(request):
    limit = _capacity(request)
    used = _pets(request).count()
    if limit is not None and used >= limit:
        return render(request, "pets/pet_limit.html", {"limit": limit, "used": used})

    form = PetForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        feeder, error = _resolve_feeder(request, form)
        if error:
            form.add_error("new_feeder_code", error)
        else:
            pet = form.save(commit=False)
            pet.owner = request.user
            ration = pet.suggested_ration()
            pet.target_grams = ration.grams_per_day
            pet.feeder = feeder
            pet.save()
            pet.ensure_schedule()
            messages.success(request, f"{pet.name} quedo registrada. Falta ensenarle sus fotos.")
            return redirect("pets:photos", pk=pet.pk)
    return render(request, "pets/pet_form.html", {"form": form, "limit": limit, "used": used})


def _resolve_feeder(request, form):
    """Devuelve (plato, error). Crea el plato si se escribio un codigo nuevo."""
    chosen = form.cleaned_data.get("feeder")
    code = (form.cleaned_data.get("new_feeder_code") or "").strip().upper()
    if not code:
        return chosen, None

    limit = _capacity(request)
    owned = Feeder.objects.filter(owner=request.user)
    if limit is not None and owned.filter(pets__isnull=True).count() == 0 and owned.count() >= limit:
        return None, f"Tu plan permite {limit} plato(s)."

    existing = Feeder.objects.filter(code=code).first()
    if existing and existing.owner_id != request.user.id:
        return None, "Ese codigo ya esta vinculado a otra cuenta."
    if existing and existing.pets.exists():
        return None, "Ese plato ya tiene una mascota asignada."
    if existing is None:
        if limit is not None and owned.count() >= limit:
            return None, f"Tu plan permite {limit} plato(s)."
        existing = Feeder.objects.create(owner=request.user, code=code, is_online=False)
    return existing, None


@login_required
def pet_photos(request, pk):
    """Fotos de referencia: de aqui sale el vector con el que la IA la reconoce."""
    pet = get_object_or_404(_pets(request), pk=pk)
    form = PetPhotoForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        uploaded = [
            ("front", form.cleaned_data.get("front")),
            ("side", form.cleaned_data.get("side")),
            ("top", form.cleaned_data.get("top")),
        ]
        added = 0
        for pose, image in uploaded:
            if not image:
                continue
            data = image.read()
            vector = embedding.describe_bytes(data)
            puntos = features.encode(features.descriptors(features.decode_bgr(data)))
            image.seek(0)
            PetPhoto.objects.create(
                pet=pet, image=image, pose=pose, embedding=vector, keypoints=puntos
            )
            added += 1
        if added:
            photos = list(pet.photos.all())
            pet.centroid = embedding.centroid([photo.embedding for photo in photos])
            pet.keypoints = features.combine([photo.keypoints for photo in photos])
            pet.save(update_fields=["centroid", "keypoints"])
            messages.success(request, f"{added} fotos guardadas. {pet.name} ya se puede reconocer.")
            return redirect("pets:ration", pk=pet.pk)
        form.add_error(None, "Sube al menos una foto.")
    poses = [
        ("front", "Frente al plato", "La cara y el hocico mirando al comedero."),
        ("side", "De perfil", "La silueta de lado: largo, patas y cola."),
        ("top", "Desde arriba", "El lomo y el tamano, de espaldas al plato."),
    ]
    return render(
        request,
        "pets/pet_photos.html",
        {"pet": pet, "form": form, "photos": pet.photos.all(), "poses": poses},
    )


@login_required
def pet_edit(request, pk):
    pet = get_object_or_404(_pets(request), pk=pk)
    form = PetForm(request.POST or None, instance=pet, user=request.user)
    if request.method == "POST" and form.is_valid():
        feeder, error = _resolve_feeder(request, form)
        if error:
            form.add_error("new_feeder_code", error)
        else:
            updated = form.save(commit=False)
            if feeder is not None:
                updated.feeder = feeder
            updated.target_grams = updated.suggested_ration().grams_per_day
            updated.save()
            messages.success(request, "Ficha actualizada.")
            return redirect("pets:detail", pk=pet.pk)
    return render(request, "pets/pet_form.html", {"form": form, "pet": pet})


@login_required
def pet_ration(request, pk):
    pet = get_object_or_404(_pets(request), pk=pk)
    ration = pet.suggested_ration()
    if request.method == "POST":
        grams = request.POST.get("grams")
        if grams:
            pet.target_grams = grams
            pet.save(update_fields=["target_grams"])
        messages.success(request, "Racion guardada.")
        return redirect("pets:detail", pk=pet.pk)
    return render(request, "pets/pet_ration.html", {"pet": pet, "ration": ration})


@login_required
def pet_archive(request, pk):
    pet = get_object_or_404(_pets(request), pk=pk)
    if request.method == "POST":
        # Archivar libera el plato: la mascota deja de usarlo y puede ir a otra.
        liberado = pet.feeder.code if pet.feeder else ""
        pet.archived = True
        pet.feeder = None
        pet.save(update_fields=["archived", "feeder"])
        extra = f" El plato {liberado} quedo libre." if liberado else ""
        messages.success(request, f"{pet.name} quedo archivada. El historial se conserva.{extra}")
        return redirect("pets:list")
    return render(request, "pets/pet_archive.html", {"pet": pet})


@login_required
def pet_restore(request, pk):
    """Devuelve una mascota archivada a la lista, sin plato asignado."""
    pet = get_object_or_404(Pet.objects.filter(owner=request.user, archived=True), pk=pk)
    if request.method == "POST":
        limit = _capacity(request)
        if limit is not None and _pets(request).count() >= limit:
            messages.error(request, f"Tu plan permite {limit} mascota(s) activas. Archiva o sube de plan.")
        else:
            pet.archived = False
            pet.save(update_fields=["archived"])
            messages.success(request, f"{pet.name} volvio a la lista. Asignale un plato para que coma.")
        return redirect("pets:settings")
    return redirect("pets:settings")


@login_required
def pet_unassign_feeder(request, pk):
    """Quita el plato de la mascota sin borrarlo de la cuenta."""
    pet = get_object_or_404(_pets(request), pk=pk)
    if request.method == "POST" and pet.feeder_id:
        code = pet.feeder.code
        pet.feeder = None
        pet.save(update_fields=["feeder"])
        messages.success(request, f"{pet.name} quedo sin plato. El plato {code} sigue en tu cuenta, libre.")
        return redirect("pets:detail", pk=pet.pk)
    return redirect("pets:detail", pk=pet.pk)


@login_required
def history(request):
    period = request.GET.get("periodo", "7")
    pets = _pets(request)
    qs = MealEvent.objects.filter(pet__in=pets).select_related("pet")
    today = timezone.localdate()
    if period == "hoy":
        qs = qs.filter(occurred_at__date=today)
    elif period == "30":
        qs = qs.filter(occurred_at__date__gte=today - timedelta(days=30))
    else:
        period = "7"
        qs = qs.filter(occurred_at__date__gte=today - timedelta(days=7))

    total = qs.aggregate(t=Sum("served_grams"))["t"] or 0
    count = qs.count()
    avg = qs.aggregate(a=Avg("eaten_grams"))["a"] or 0
    return render(request, "pets/history.html", {
        "events": qs[:8],
        "period": period,
        "total": total,
        "count": count,
        "avg": avg,
    })


@login_required
def alerts(request):
    pets = _pets(request)
    items = Alert.objects.filter(pet__in=pets).select_related("pet")
    if request.method == "POST":
        items.filter(read_at__isnull=True).update(read_at=timezone.now())
        messages.success(request, "Alertas marcadas como leidas.")
        return redirect("pets:alerts")
    return render(request, "pets/alerts.html", {
        "alerts": items[:10],
        "unread": items.filter(read_at__isnull=True).count(),
    })


@login_required
def settings_view(request):
    feeders = Feeder.objects.filter(owner=request.user).prefetch_related("pets")
    limit = _capacity(request)
    return render(request, "pets/settings.html", {
        "feeders": feeders,
        "pets": _pets(request),
        "limit": limit,
        "can_add_feeder": limit is None or feeders.count() < limit,
        "archived_pets": Pet.objects.filter(owner=request.user, archived=True),
    })


@login_required
def feeder_add(request):
    if request.method != "POST":
        return redirect("pets:settings")
    code = (request.POST.get("code") or "").strip().upper()
    limit = _capacity(request)
    owned = Feeder.objects.filter(owner=request.user)
    if not code:
        messages.error(request, "Escribe el codigo del plato.")
    elif limit is not None and owned.count() >= limit:
        messages.error(request, f"Tu plan permite {limit} plato(s).")
    elif Feeder.objects.filter(code=code).exclude(owner=request.user).exists():
        messages.error(request, "Ese codigo ya esta vinculado a otra cuenta.")
    elif owned.filter(code=code).exists():
        messages.info(request, "Ese plato ya esta en tu cuenta.")
    else:
        Feeder.objects.create(owner=request.user, code=code, is_online=False)
        messages.success(request, f"Plato {code} vinculado. Asignalo a una mascota para que funcione.")
    return redirect("pets:settings")


@login_required
def events(request):
    """Horarios de comida y ordenes al comedero.

    Solo existe en la instalacion local: en la nube no hay ESP32 que controlar,
    asi que la pagina no se publica.
    """
    if not settings.IS_LOCAL:
        raise Http404("Este panel solo existe en la instalacion local.")

    pets = _pets(request).filter(archived=False)

    if request.method == "POST":
        accion = request.POST.get("accion", "agregar")

        if accion == "agregar":
            pet = pets.filter(pk=request.POST.get("pet")).first()
            hora = (request.POST.get("time") or "").strip()
            gramos = (request.POST.get("grams") or "").strip()

            if pet is None or not hora:
                messages.error(request, "Elige la mascota y la hora.")
            else:
                if not gramos:
                    comidas = pet.meals_per_day or 2
                    gramos = round(float(pet.target_grams or 0) / comidas, 1)
                try:
                    MealTime.objects.create(pet=pet, time=hora, grams=gramos)
                    messages.success(
                        request, "%s: comida a las %s con %s g." % (pet.name, hora[:5], gramos)
                    )
                except (ValueError, TypeError):
                    messages.error(request, "Esa hora o ese peso no son validos.")

        elif accion == "borrar":
            comida = MealTime.objects.filter(
                pk=request.POST.get("meal"), pet__owner=request.user
            ).first()
            if comida is not None:
                comida.delete()
                messages.success(request, "Horario eliminado.")

        elif accion == "servir":
            # Va directo al equipo: no depende del plato, ni de MQTT, ni de la
            # Raspberry. Es una prueba de hardware.
            pet = pets.filter(pk=request.POST.get("pet")).first()
            if pet is None:
                messages.error(request, "Elige una mascota.")
            else:
                comidas = pet.meals_per_day or 2
                gramos = round(float(pet.target_grams or 0) / comidas, 1)
                try:
                    # Sin "open": el plato se llena con la tapa cerrada y la
                    # placa la abre sola cuando termina de servir.
                    _device_post("/api/dose", {"pet": pet.name, "grams": gramos})
                    messages.success(
                        request, "Sirviendo %s g a %s en el comedero." % (gramos, pet.name)
                    )
                except requests.RequestException as exc:
                    messages.error(request, "El comedero no respondio: %s" % exc)

        elif accion == "reset":
            try:
                _device_post("/api/reset")
                messages.success(
                    request, "Comedero en reposo: motor parado, tapa cerrada."
                )
            except requests.RequestException as exc:
                messages.error(request, "El comedero no respondio: %s" % exc)

        elif accion == "reboot":
            try:
                _device_post("/api/reboot")
                messages.success(request, "Reiniciando la placa. Tarda unos segundos.")
            except requests.RequestException as exc:
                messages.error(request, "El comedero no respondio: %s" % exc)

        elif accion == "orden":
            comedero = Feeder.objects.filter(
                owner=request.user, pk=request.POST.get("feeder")
            ).first()
            if comedero is not None:
                FeederCommand.objects.create(
                    feeder=comedero, action=request.POST.get("action", "reconnect")
                )
                messages.success(request, "Orden enviada a %s." % comedero.code)

        return redirect("pets:events")

    comederos = Feeder.objects.filter(owner=request.user).order_by("code")

    # La porcion que se sirve en cada comida, para mostrarla en el boton.
    lista = list(pets)
    for pet in lista:
        comidas = pet.meals_per_day or 2
        pet.portion = round(float(pet.target_grams or 0) / comidas, 1)

    return render(
        request,
        "pets/events.html",
        {"pets": lista, "comederos": comederos, "device": _dispositivo()},
    )


@login_required
def feeder_command(request, pk):
    feeder = get_object_or_404(Feeder.objects.filter(owner=request.user), pk=pk)
    if request.method == "POST":
        FeederCommand.objects.create(feeder=feeder, action="reconnect")
        messages.success(request, f"Pedido de reconexion enviado a {feeder.code}.")
    return redirect("pets:settings")


@login_required
def feeder_delete(request, pk):
    feeder = get_object_or_404(Feeder.objects.filter(owner=request.user), pk=pk)
    if request.method == "POST":
        for pet in feeder.pets.all():
            pet.feeder = None
            pet.save(update_fields=["feeder"])
        feeder.delete()
        messages.success(request, "Plato desvinculado.")
        return redirect("pets:settings")
    return render(request, "pets/feeder_delete.html", {"feeder": feeder})


# --- vista en vivo: peso y camara del ESP32 -------------------------------

def _dispositivo():
    """IP del comedero: la que anota la Raspberry, o la del .env como respaldo."""
    from pathlib import Path

    anotada = Path(settings.BASE_DIR).parent / ".device-ip"
    try:
        ip = anotada.read_text(encoding="utf-8").strip()
    except OSError:
        ip = ""
    if ip:
        return "http://" + ip
    return getattr(settings, "DEVICE_URL", "")


def _device_post(ruta, datos=None):
    """Habla directo con el ESP32. Se usa en el panel de pruebas."""
    respuesta = requests.post(_dispositivo() + ruta, json=datos or {}, timeout=6)
    respuesta.raise_for_status()
    return respuesta.json()


@login_required
def live_state(request):
    """Reenvia el estado del ESP32 para que el navegador no hable con el plato."""
    if not settings.IS_LOCAL:
        raise Http404("Sin equipo local.")
    try:
        respuesta = requests.get(_dispositivo() + "/api/state", timeout=(3, 8))
        respuesta.raise_for_status()
        return JsonResponse(respuesta.json())
    except requests.RequestException as exc:
        return JsonResponse({"online": False, "error": str(exc)}, status=502)


@login_required
def live_video(request):
    """Proxy del MJPEG. Solo transmite si el sensor ve algo."""
    if not settings.IS_LOCAL:
        raise Http404("Sin equipo local.")
    try:
        estado = requests.get(_dispositivo() + "/api/state", timeout=(3, 8)).json()
    except (requests.RequestException, ValueError):
        raise Http404("comedero sin respuesta")

    if not estado.get("presence"):
        return StreamingHttpResponse(iter(()), status=204)

    try:
        flujo = requests.get(
            _dispositivo() + "/stream",
            stream=True,
            timeout=(4, 30),
        )
    except requests.RequestException:
        raise Http404("sin video")

    if flujo.status_code != 200:
        raise Http404("sin video")

    def trozos():
        try:
            for trozo in flujo.iter_content(chunk_size=4096):
                if trozo:
                    yield trozo
        finally:
            flujo.close()

    respuesta = StreamingHttpResponse(
        trozos(),
        content_type=flujo.headers.get("Content-Type", "multipart/x-mixed-replace"),
    )
    respuesta["Cache-Control"] = "no-store"
    return respuesta


# --- registrar las tomas con la camara del plato --------------------------

def _foto_del_equipo(ancho=15) -> bytes:
    """Pide una foto al ESP32.

    El enlace del comedor es irregular: la misma peticion tarda entre 0,2 y 5 s.
    Se reintenta una vez y se da mas margen que antes, para que un pico de
    latencia no se convierta en un error en la cara del usuario.
    """
    ultimo = None
    for _ in range(2):
        try:
            respuesta = requests.get(
                _dispositivo() + "/capture?size=vga", timeout=(4, ancho)
            )
            respuesta.raise_for_status()
            return respuesta.content
        except requests.RequestException as exc:
            ultimo = exc
    raise ultimo


@login_required
def pet_preview(request, pk):
    """Una foto suelta de la camara del plato, para encuadrar en vivo."""
    if not settings.IS_LOCAL:
        raise Http404("Sin equipo local.")
    get_object_or_404(_pets(request), pk=pk)
    try:
        datos = _foto_del_equipo()
    except requests.RequestException:
        raise Http404("La camara del plato no responde.")
    return HttpResponse(datos, content_type="image/jpeg")


@login_required
@require_POST
def pet_capture(request, pk, pose):
    """Guarda una toma hecha con la camara del plato, sin subir archivos."""
    if not settings.IS_LOCAL:
        raise Http404("Sin equipo local.")

    pet = get_object_or_404(_pets(request), pk=pk)
    if pose not in ("front", "side", "top"):
        raise Http404("Toma desconocida.")

    try:
        datos = _foto_del_equipo()
    except requests.RequestException as exc:
        messages.error(request, "La camara del plato no respondio: %s" % exc)
        return redirect("pets:photos", pk=pet.pk)

    vector = embedding.describe_bytes(datos)
    puntos = features.encode(features.descriptors(features.decode_bgr(datos)))

    # Reemplaza solo esa toma: las otras dos se conservan.
    pet.photos.filter(pose=pose).delete()
    foto = PetPhoto(pet=pet, pose=pose, embedding=vector, keypoints=puntos)
    foto.image.save("%s-%s.jpg" % (pet.pk, pose), ContentFile(datos), save=True)

    fotos = list(pet.photos.all())
    pet.centroid = embedding.centroid([f.embedding for f in fotos])
    pet.keypoints = features.combine([f.keypoints for f in fotos])
    pet.save(update_fields=["centroid", "keypoints"])

    messages.success(
        request,
        "Toma guardada. %s tiene %d tomas." % (pet.name, len(fotos)),
    )
    return redirect("pets:photos", pk=pet.pk)
