"""Reconoce la mascota comparando con el vector que guardo la web."""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from . import descriptor

log = logging.getLogger(__name__)


class PetRecognizer:
    def __init__(self, photos_dir: Path | None = None):
        self.photos_dir = Path(photos_dir) if photos_dir else None
        self._profiles: dict[str, list[float]] = {}
        self.reload_from_disk()

    # --- fuentes de perfiles ---------------------------------------------
    def load_profiles(self, pets: list[dict]) -> None:
        """Perfiles que llegan de la web: el vector guardado al registrarla."""
        loaded = {}
        for pet in pets:
            vector = pet.get("centroid") or []
            if len(vector) == descriptor.DIMENSIONS:
                loaded[pet["name"]] = vector
        if loaded:
            self._profiles = loaded
            log.info("Perfiles desde la web: %s", ", ".join(sorted(loaded)))
        elif not self._profiles:
            log.warning("La web no tiene vectores guardados todavia")

    def reload_from_disk(self) -> None:
        """Respaldo: fotos sueltas en disco, para pruebas sin web."""
        if not self.photos_dir or not self.photos_dir.exists():
            return
        profiles = {}
        for pet_dir in sorted(self.photos_dir.iterdir()):
            if not pet_dir.is_dir():
                continue
            vectors = [
                descriptor.describe_bytes(p.read_bytes())
                for p in sorted(pet_dir.glob("*.jpg"))
            ]
            vector = descriptor.centroid(vectors)
            if vector:
                profiles[pet_dir.name] = vector
        if profiles:
            self._profiles.update(profiles)

    @property
    def pets(self) -> list[str]:
        return sorted(self._profiles)

    # --- reconocimiento ---------------------------------------------------
    def identify(self, frames: list[np.ndarray]) -> tuple[str | None, float]:
        if not frames or not self._profiles:
            return None, 0.0
        vectors = [descriptor.describe_array(frame) for frame in frames]
        vector = descriptor.centroid(vectors)
        if not vector:
            return None, 0.0
        best_name, best_score = None, 0.0
        for name, centroid in self._profiles.items():
            score = descriptor.similarity(vector, centroid)
            if score > best_score:
                best_name, best_score = name, score
        return best_name, round(best_score, 3)
