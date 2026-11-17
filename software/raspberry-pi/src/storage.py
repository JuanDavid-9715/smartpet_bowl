"""Guarda en el Django local y encola la sincronizacion a la nube."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import requests

from . import config

log = logging.getLogger(__name__)
QUEUE = Path(__file__).resolve().parent.parent / "pending.jsonl"


def payload(events: list[dict], alerts: list[dict] | None = None, online: bool = True) -> dict:
    return {
        "feeder": config.FEEDER_CODE,
        "online": online,
        "events": events,
        "alerts": alerts or [],
    }


def _post(url: str, token: str, body: dict) -> bool:
    if not url:
        return False
    try:
        response = requests.post(
            url,
            data=json.dumps(body),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            timeout=8,
        )
        return response.status_code < 400
    except requests.RequestException as exc:
        log.warning("No se pudo publicar en %s: %s", url, exc)
        return False


def save(body: dict) -> None:
    """Local primero. Si falla, queda en cola para reintentar."""
    ok = _post(config.LOCAL_API, config.INGEST_TOKEN, body)
    if not ok:
        with QUEUE.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(body) + "\n")
    sync_cloud()


def sync_cloud() -> None:
    if not config.CLOUD_API:
        return
    _post(config.CLOUD_API, config.CLOUD_TOKEN, {"ping": True})
    if not QUEUE.exists():
        return
    remaining = []
    for line in QUEUE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        body = json.loads(line)
        if not _post(config.CLOUD_API, config.CLOUD_TOKEN, body):
            remaining.append(line)
    QUEUE.write_text("\n".join(remaining), encoding="utf-8")


def fetch_plan() -> dict:
    base = config.LOCAL_API.rsplit("/api/", 1)[0]
    try:
        response = requests.get(
            f"{base}/api/v1/plan/",
            params={"feeder": config.FEEDER_CODE},
            headers={"Authorization": f"Bearer {config.INGEST_TOKEN}"},
            timeout=6,
        )
        if response.status_code < 400:
            return response.json()
    except requests.RequestException as exc:
        log.warning("Sin plan local: %s", exc)
    return {"pets": []}
