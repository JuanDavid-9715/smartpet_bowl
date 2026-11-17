"""Captura del MJPEG del ESP32 y extraccion de caracteristicas.

Sin API externa y sin entrenamiento: el modelo se descarga una vez y se usa
congelado como extractor. Si el modelo no esta, cae a un descriptor de color
que sirve para separar un gato atigrado de un boxer.
"""
from __future__ import annotations

import cv2
import numpy as np

try:
    import onnxruntime as ort
except ImportError:
    ort = None


class FrameSource:
    def __init__(self, url: str, timeout: float = 6.0):
        self.url = url
        self.timeout = timeout

    def grab(self, count: int = 8) -> list[np.ndarray]:
        if not self.url:
            return []
        capture = cv2.VideoCapture(self.url)
        frames: list[np.ndarray] = []
        try:
            for _ in range(count * 3):
                ok, frame = capture.read()
                if not ok:
                    break
                frames.append(frame)
                if len(frames) >= count:
                    break
        finally:
            capture.release()
        return frames


class FeatureExtractor:
    """Devuelve un vector por cuadro."""

    def __init__(self, model_path=None):
        self.session = None
        if model_path and ort is not None:
            try:
                self.session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
                self.input_name = self.session.get_inputs()[0].name
            except Exception:
                self.session = None

    @property
    def backend(self) -> str:
        return "onnx" if self.session else "color"

    def _preprocess(self, frame: np.ndarray) -> np.ndarray:
        img = cv2.resize(frame, (224, 224)).astype(np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        img = (img - mean) / std
        return np.transpose(img, (2, 0, 1))[None, ...]

    def describe(self, frame: np.ndarray) -> np.ndarray:
        if self.session is not None:
            out = self.session.run(None, {self.input_name: self._preprocess(frame)})[0]
            vector = np.ravel(out)
        else:
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hsv], [0, 1], None, [16, 16], [0, 180, 0, 256])
            cv2.normalize(hist, hist)
            vector = hist.ravel()
        norm = np.linalg.norm(vector) or 1.0
        return vector / norm

    def describe_many(self, frames: list[np.ndarray]) -> np.ndarray:
        if not frames:
            return np.zeros((0, 1))
        vectors = [self.describe(frame) for frame in frames]
        return np.vstack(vectors)

    @staticmethod
    def similarity(a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b))
