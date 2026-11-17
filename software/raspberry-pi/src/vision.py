"""Captura del MJPEG que sirve el ESP32-S3.

Solo obtiene cuadros. El vector lo calcula src/descriptor.py, que es el mismo
algoritmo que usa la web al registrar la mascota.
"""
from __future__ import annotations

import cv2
import numpy as np



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


# El descriptor de imagen vive en src/descriptor.py, y es el mismo que usa la web
# para guardar el vector de cada mascota. El camino con red neuronal (ONNX) queda
# pendiente: exigiria recalcular los vectores ya guardados.
