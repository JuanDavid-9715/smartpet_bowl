"""Orquestacion: presencia, identificacion, servido, pesaje y sobrante."""
from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path
import threading
import time
import uuid

from . import config, feeding, features, storage
from .client import MqttClient
from .recognizer import PetRecognizer
from .vision import FrameSource

log = logging.getLogger(__name__)

CALL_SECONDS = 20
PLAN_TTL = 300


class FeedingService:
    def __init__(self):
        self.source = FrameSource(config.STREAM_URL)
        self._board_ip = ""
        self.recognizer = PetRecognizer(config.PET_PHOTOS_DIR)
        self.mqtt = MqttClient(self.handle_message)
        self.sessions: dict[str, feeding.Session] = {}
        self.leftover_pending: dict[str, float] = {}
        self._plan: dict = {"pets": []}
        self._plan_at = 0.0
        self._stop = threading.Event()
        # El sensor de presencia avisa muchas veces mientras la mascota esta
        # delante. Sin este candado cada aviso lanzaba otra identificacion y se
        # apilaban: el servicio parecia congelado y la placa no daba abasto.
        self._identificando = threading.Lock()
        log.info("Reconocimiento: ORB %d puntos · mascotas: %s",
                 features.ORB_FEATURES, ", ".join(self.recognizer.pets) or "ninguna")

    # --- plan -------------------------------------------------------------
    def plan(self) -> list[dict]:
        if time.time() - self._plan_at > PLAN_TTL:
            self._plan = storage.fetch_plan()
            self._plan_at = time.time()
            self.recognizer.load_profiles(self._plan.get("pets", []))
            for pet in self._plan.get("pets", []):
                if pet["name"] not in self.recognizer.pets:
                    log.warning("Sin fotos de referencia para %s", pet["name"])
        return self._plan.get("pets", [])

    def _planned_grams(self, pet_name: str) -> float:
        for pet in self.plan():
            if pet["name"].lower() == pet_name.lower():
                grams = pet.get("target_grams", 0)
                meals = len(pet.get("meals") or []) or 2
                portion = round(grams / meals, 1)
                return feeding.adjust_for_leftover(portion, self.leftover_pending.get(pet_name, 0))
        return 0.0

    # --- llegada del animal ----------------------------------------------
    def on_presence(self) -> None:
        # Si ya hay una identificacion en curso se ignora el aviso: la mascota
        # sigue delante y el sensor repite. Encadenarlas era lo que hacia que el
        # servicio pareciera congelado.
        if not self._identificando.acquire(blocking=False):
            return

        try:
            frames = self.source.grab()
            if not frames:
                log.warning("Sin cuadros de la camara. Revisa STREAM_URL")
                self.mqtt.publish("cerrar", {"motivo": "sin_video"})
                return

            pet, score = self.recognizer.identify(frames)
            if pet and score >= config.CONFIDENCE_THRESHOLD:
                grams = self._planned_grams(pet)
                self.sessions[pet] = feeding.Session(pet=pet, planned=grams, confidence=score)
                self.mqtt.publish("servir", {"mascota": pet, "gramos": grams, "confianza": score})
                log.info("Identificada %s (%.2f) · servir %.1f g", pet, score, grams)
            else:
                self.mqtt.publish("cerrar", {"motivo": "no_identificada", "confianza": score})
                log.info("No identificada (mejor %.2f) · cerrar", score)
        finally:
            self._identificando.release()

    # --- eventos del comedero --------------------------------------------
    def handle_message(self, topic: str, body: dict) -> None:
        name = topic.rsplit("/", 1)[-1]
        if name == "presencia":
            self.on_presence()
        elif name == "peso":
            self.on_weight(body)
        elif name == "sobrante":
            self.on_leftover(body)
        elif name == "ip":
            self._anotar_ip(str(body.get("ip", "")))
        elif name == "estado":
            log.info("Estado del comedero: %s", body)

    def on_weight(self, body: dict) -> None:
        pet = body.get("mascota") or (next(iter(self.sessions), None))
        if pet and pet in self.sessions:
            self.sessions[pet].served = float(body.get("gramos", 0) or 0)
            log.info("%s: servido %.1f g", pet, self.sessions[pet].served)

    def on_leftover(self, body: dict) -> None:
        pet = body.get("mascota") or (next(iter(self.sessions), None))
        if not pet:
            return
        session = self.sessions.pop(pet, None)
        leftover = float(body.get("gramos", 0) or 0)
        if session is None:
            # Sin sesion no hubo comida: nadie fue identificado. Antes se
            # inventaba una sesion con la porcion programada y quedaba en el
            # historial "Jiru comio 65.6 de 65.6 g" sin haber comido.
            log.warning(
                "Sobrante de %.1f g para %s sin sesion: no se registra la comida",
                leftover,
                pet,
            )
            return
        session.leftover = leftover
        self.leftover_pending[pet] = leftover
        event = {
            "uid": body.get("uid") or str(uuid.uuid4()),
            "pet": pet,
            "occurred_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "scheduled_grams": session.planned,
            "served_grams": session.served,
            "leftover_grams": leftover,
            "eaten_grams": session.eaten,
            "status": session.status,
            "confidence": session.confidence,
            "duration_seconds": int(body.get("duracion_s", 0) or 0),
        }
        alerts = []
        if session.served and leftover / session.served >= 0.5:
            alerts.append({
                "severity": "alert",
                "title": f"{pet} dejo {leftover:.0f} g en el plato",
                "detail": "Sobrante alto. Conviene limpiar el plato antes de la siguiente comida.",
            })
        elif session.served and leftover / session.served >= 0.2:
            alerts.append({
                "severity": "warning",
                "title": f"{pet} dejo parte de su racion",
                "detail": f"Sobrante de {leftover:.0f} g sobre {session.served:.0f} g servidos.",
            })
        storage.save(storage.payload([event], alerts))
        log.info("%s: comio %.1f de %.1f g (%s)", pet, session.eaten, session.served, session.status)

    def _anotar_ip(self, ip: str) -> None:
        """La placa cambia de IP con el hotspot: se sigue sola."""
        if not ip or ip == self._board_ip:
            return
        self._board_ip = ip
        self.source = FrameSource(f"http://{ip}/capture?size=vga")
        destino = Path(__file__).resolve().parents[2] / ".device-ip"
        try:
            destino.write_text(ip, encoding="utf-8")
        except OSError as exc:
            log.warning("No pude anotar la IP: %s", exc)
        log.info("Comedero en %s", ip)

    # --- horario ----------------------------------------------------------
    def scheduler(self) -> None:
        while not self._stop.is_set():
            now = dt.datetime.now().strftime("%H:%M")
            for pet in self.plan():
                for meal in pet.get("meals", []):
                    if meal["time"] == now:
                        grams = feeding.adjust_for_leftover(
                            meal["grams"], self.leftover_pending.get(pet["name"], 0)
                        )
                        self.mqtt.publish("llamada", {
                            "mascota": pet["name"],
                            "gramos": grams,
                            "segundos": CALL_SECONDS,
                        })
                        log.info("Llamada para %s: %.1f g", pet["name"], grams)
                        time.sleep(61)
            for command in storage.fetch_commands():
                accion = command.get("action")
                if accion == "feed":
                    # "Servir ahora" desde el panel tecnico: no espera la hora.
                    self.mqtt.publish("llamada", {
                        "mascota": command.get("target", ""),
                        "gramos": command.get("grams", 0),
                        "segundos": CALL_SECONDS,
                    })
                    log.info(
                        "Servir ahora: %.1f g a %s",
                        float(command.get("grams") or 0), command.get("target", ""),
                    )
                elif accion in ("reconnect", "restart"):
                    self.mqtt.publish("reiniciar", {"motivo": "pedido desde la web"})
                    log.info("Orden atendida: %s", accion)
            self._stop.wait(20)

    def run(self) -> None:
        self.mqtt.connect()
        thread = threading.Thread(target=self.scheduler, daemon=True)
        thread.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self) -> None:
        self._stop.set()
        self.mqtt.stop()
