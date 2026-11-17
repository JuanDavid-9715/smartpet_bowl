from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from telemetry.models import Alert, MealEvent

from . import nutrition
from .forms import PetForm, PetPhotoForm
from . import embedding
from .models import Feeder, FeederCommand, Pet, PetPhoto


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
            ("eating", form.cleaned_data.get("eating")),
            ("top", form.cleaned_data.get("top")),
        ]
        added = 0
        for pose, image in uploaded:
            if not image:
                continue
            data = image.read()
            vector = embedding.describe_bytes(data)
            image.seek(0)
            PetPhoto.objects.create(pet=pet, image=image, pose=pose, embedding=vector)
            added += 1
        if added:
            vectors = [photo.embedding for photo in pet.photos.all()]
            pet.centroid = embedding.centroid(vectors)
            pet.save(update_fields=["centroid"])
            messages.success(request, f"{added} fotos guardadas. {pet.name} ya se puede reconocer.")
            return redirect("pets:ration", pk=pet.pk)
        form.add_error(None, "Sube al menos una foto.")
    return render(request, "pets/pet_photos.html", {"pet": pet, "form": form, "photos": pet.photos.all()})


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
        pet.archived = True
        pet.save(update_fields=["archived"])
        messages.success(request, f"{pet.name} quedo archivada. El historial se conserva.")
        return redirect("pets:list")
    return render(request, "pets/pet_archive.html", {"pet": pet})


@login_required
def assign_feeder(request, pk):
    pet = get_object_or_404(_pets(request), pk=pk)
    feeders = Feeder.objects.filter(owner=request.user)
    if request.method == "POST":
        feeder_id = request.POST.get("feeder")
        pet.feeder = feeders.filter(pk=feeder_id).first()
        pet.save(update_fields=["feeder"])
        messages.success(request, "Comedero asignado.")
        return redirect("pets:detail", pk=pet.pk)
    return render(request, "pets/pet_feeder.html", {"pet": pet, "feeders": feeders})


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
