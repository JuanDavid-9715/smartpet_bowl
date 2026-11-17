from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from telemetry.models import Alert, MealEvent

from . import nutrition
from .forms import PetForm
from .models import Feeder, Pet


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
    capacity = 4 if request.user.pets.count() > 1 else 1
    return render(request, "pets/pet_list.html", {
        "pets": pets,
        "capacity": capacity,
        "used": len(pets),
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


@login_required
def pet_create(request):
    form = PetForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        pet = form.save(commit=False)
        pet.owner = request.user
        ration = pet.suggested_ration()
        pet.target_grams = ration.grams_per_day
        pet.save()
        pet.ensure_schedule()
        messages.success(request, f"{pet.name} quedo registrada con {ration.grams_per_day} g al dia.")
        return redirect("pets:ration", pk=pet.pk)
    return render(request, "pets/pet_form.html", {"form": form})


@login_required
def pet_edit(request, pk):
    pet = get_object_or_404(_pets(request), pk=pk)
    form = PetForm(request.POST or None, instance=pet)
    if request.method == "POST" and form.is_valid():
        pet = form.save(commit=False)
        pet.target_grams = pet.suggested_ration().grams_per_day
        pet.save()
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
    return render(request, "pets/settings.html", {
        "feeders": Feeder.objects.filter(owner=request.user),
        "pets": _pets(request),
    })
