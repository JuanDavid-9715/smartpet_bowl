"""Ingesta de datos que publica la Raspberry. Idempotente por uid de evento."""
import json
import uuid
from datetime import datetime

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from pets.models import Feeder, FeederCommand, Pet
from telemetry.models import Alert, MealEvent


def _authorized(request) -> bool:
    header = request.headers.get("Authorization", "")
    token = header.replace("Bearer ", "").strip() or request.headers.get("X-Ingest-Token", "").strip()
    return bool(token) and token == settings.INGEST_TOKEN


def _parse_dt(value):
    if not value:
        return timezone.now()
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return timezone.now()


@csrf_exempt
@require_POST
def ingest(request):
    if not _authorized(request):
        return JsonResponse({"error": "token invalido"}, status=401)
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": "json invalido"}, status=400)

    code = str(payload.get("feeder", "")).strip()
    feeder = Feeder.objects.filter(code=code).first()
    if feeder is None:
        return JsonResponse({"error": f"comedero desconocido: {code}"}, status=404)

    feeder.is_online = bool(payload.get("online", True))
    if "firmware" in payload:
        feeder.firmware = str(payload["firmware"])[:40]
    feeder.last_sync = timezone.now()
    feeder.save(update_fields=["is_online", "firmware", "last_sync"])

    created = updated = skipped = 0
    for item in payload.get("events", []):
        pet_name = str(item.get("pet", "")).strip()
        pet = feeder.pets.filter(name__iexact=pet_name).first() if pet_name else None
        if pet is None and feeder.pets.count() == 1:
            pet = feeder.pets.first()
        if pet is None:
            continue
        raw_uid = item.get("uid")
        if not raw_uid:
            skipped += 1
            continue
        try:
            uid = uuid.UUID(str(raw_uid))
        except (ValueError, AttributeError, TypeError):
            skipped += 1
            continue
        defaults = {
            "pet": pet,
            "feeder": feeder,
            "occurred_at": _parse_dt(item.get("occurred_at")),
            "scheduled_grams": item.get("scheduled_grams", 0) or 0,
            "served_grams": item.get("served_grams", 0) or 0,
            "leftover_grams": item.get("leftover_grams", 0) or 0,
            "eaten_grams": item.get("eaten_grams", 0) or 0,
            "status": item.get("status", "ate"),
            "confidence": float(item.get("confidence", 0) or 0),
            "duration_seconds": int(item.get("duration_seconds", 0) or 0),
            "synced": not settings.IS_LOCAL,
        }
        obj, was_created = MealEvent.objects.update_or_create(event_uid=uid, defaults=defaults)
        created += 1 if was_created else 0
        updated += 0 if was_created else 1

    for alert in payload.get("alerts", []):
        Alert.objects.create(
            feeder=feeder,
            severity=alert.get("severity", "warning"),
            title=str(alert.get("title", ""))[:140],
            detail=str(alert.get("detail", ""))[:240],
        )

    return JsonResponse({"ok": True, "created": created, "updated": updated, "skipped": skipped})


def health(request):
    return JsonResponse({"ok": True, "deployment": settings.DEPLOYMENT})


def plan(request):
    """Horarios y raciones que la Raspberry usa para saber a quien servir."""
    if not _authorized(request):
        return JsonResponse({"error": "token invalido"}, status=401)
    code = request.GET.get("feeder", "").strip()
    feeder = Feeder.objects.filter(code=code).first()
    if feeder is None:
        return JsonResponse({"error": "comedero desconocido"}, status=404)
    pets = []
    for pet in feeder.pets.filter(archived=False):
        pets.append({
            "name": pet.name,
            "species": pet.species,
            "target_grams": float(pet.target_grams or 0),
            "feeder": pet.feeder.code if pet.feeder else "",
            "centroid": pet.centroid or [],
            "keypoints": pet.keypoints or "",
            "meals": [
                {"time": meal.time.strftime("%H:%M"), "grams": float(meal.grams)}
                for meal in pet.meal_times.all()
            ],
        })
    return JsonResponse({"feeder": feeder.code, "pets": pets})


@csrf_exempt
def commands(request):
    """La Raspberry recoge las ordenes pendientes y las marca como enviadas."""
    if not _authorized(request):
        return JsonResponse({"error": "token invalido"}, status=401)
    code = request.GET.get("feeder", "").strip()
    feeder = Feeder.objects.filter(code=code).first()
    if feeder is None:
        return JsonResponse({"error": "comedero desconocido"}, status=404)
    pending = list(feeder.commands.filter(sent_at__isnull=True))
    payload = [{"id": cmd.pk, "action": cmd.action} for cmd in pending]
    if pending:
        feeder.commands.filter(pk__in=[c.pk for c in pending]).update(sent_at=timezone.now())
    return JsonResponse({"commands": payload})
