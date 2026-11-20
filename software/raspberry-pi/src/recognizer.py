"""Reconoce la mascota comparando puntos caracteristicos con los de la web.

Por que no se usa color: un histograma global parecia 0.909 entre dos mascotas
distintas, suficiente para confundirlas. Con ORB la misma foto da mas de 200
coincidencias y otra mascota menos de 10, y aguanta luz distinta y distancias
hasta un 30 %.
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from . import features as vision

log = logging.getLogger(__name__)


class PetRecognizer:
    def __init__(self, photos_dir: Path | None = None):
        self.photos_dir = Path(photos_dir) if photos_dir else None
        self._profiles: dict[str, np.ndarray] = {}
        self.reload_from_disk()

    # --- fuentes de perfiles ---------------------------------------------
    def load_profiles(self, pets: list[dict]) -> None:
        """Perfiles que llegan de la web: puntos caracteristicos de sus fotos."""
        loaded = {}
        for pet in pets:
            puntos = vision.decode(pet.get("keypoints") or "")
            if puntos is not None and len(puntos):
                loaded[pet["name"]] = puntos

        if loaded:
            self._profiles = loaded
            log.info(
                "Perfiles desde la web: %s",
                ", ".join("%s (%d puntos)" % (n, len(d)) for n, d in sorted(loaded.items())),
            )
        elif not self._profiles:
            log.warning("La web no tiene fotos de referencia todavia")

    def reload_from_disk(self) -> None:
        """Respaldo: fotos sueltas en disco, para pruebas sin web."""
        if not self.photos_dir or not self.photos_dir.exists():
            return
        perfiles = {}
        for carpeta in sorted(self.photos_dir.iterdir()):
            if not carpeta.is_dir():
                continue
            partes = []
            for archivo in sorted(carpeta.glob("*.jpg")):
                puntos = vision.descriptors(vision.decode_bgr(archivo.read_bytes()))
                if puntos is not None and len(puntos):
                    partes.append(puntos)
            if partes:
                perfiles[carpeta.name] = np.vstack(partes)
        if perfiles:
            self._profiles.update(perfiles)

    @property
    def pets(self) -> list[str]:
        return sorted(self._profiles)

    # --- reconocimiento ---------------------------------------------------
    def identify(self, frames: list[np.ndarray]) -> tuple[str | None, float]:
        if not frames or not self._profiles:
            return None, 0.0

        # Se suman las coincidencias de todos los cuadros: un cuadro borroso
        # aporta poco, pero no hunde la decision.
        totales = {nombre: 0 for nombre in self._profiles}
        for frame in frames:
            puntos = vision.descriptors(frame)
            if puntos is None or not len(puntos):
                continue
            for nombre, perfil in self._profiles.items():
                totales[nombre] += vision.match_score(perfil, puntos)

        ordenados = sorted(totales.items(), key=lambda par: par[1], reverse=True)
        mejor, puntaje = ordenados[0]
        segundo = ordenados[1][1] if len(ordenados) > 1 else 0

        if puntaje < vision.MIN_MATCHES:
            log.info("Sin coincidencias suficientes (mejor %s con %d)", mejor, puntaje)
            return None, 0.0

        # Confianza: que tanto domina el primero sobre el segundo.
        confianza = puntaje / (puntaje + segundo) if segundo else 1.0
        log.info(
            "Coincidencias: %s",
            ", ".join("%s=%d" % par for par in ordenados),
        )
        return mejor, round(confianza, 3)
