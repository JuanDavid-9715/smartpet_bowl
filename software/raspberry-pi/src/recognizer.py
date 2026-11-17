"""Reconoce la mascota comparando con sus fotos de referencia."""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .vision import FeatureExtractor


class PetRecognizer:
    def __init__(self, photos_dir: Path, extractor: FeatureExtractor):
        self.photos_dir = Path(photos_dir)
        self.extractor = extractor
        self._profiles: dict[str, np.ndarray] = {}
        self.reload()

    def reload(self) -> None:
        self._profiles.clear()
        if not self.photos_dir.exists():
            return
        for pet_dir in sorted(self.photos_dir.iterdir()):
            if not pet_dir.is_dir():
                continue
            vectors = []
            for image_path in sorted(pet_dir.glob("*.jpg")):
                image = cv2.imread(str(image_path))
                if image is not None:
                    vectors.append(self.extractor.describe(image))
            if vectors:
                centroid = np.mean(vectors, axis=0)
                self._profiles[pet_dir.name] = centroid / (np.linalg.norm(centroid) or 1.0)

    @property
    def pets(self) -> list[str]:
        return sorted(self._profiles)

    def identify(self, frames: list[np.ndarray]) -> tuple[str | None, float]:
        if not frames or not self._profiles:
            return None, 0.0
        vectors = self.extractor.describe_many(frames)
        best_name, best_score = None, 0.0
        for name, centroid in self._profiles.items():
            score = float(np.mean([FeatureExtractor.similarity(v, centroid) for v in vectors]))
            if score > best_score:
                best_name, best_score = name, score
        return best_name, round(best_score, 3)
