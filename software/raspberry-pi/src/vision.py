"""Captura de cuadros del ESP32-S3.

Solo obtiene cuadros. El vector lo calcula src/features.py, que es el mismo
algoritmo que usa la web al registrar la mascota.

La URL del comedero (`STREAM_URL`) apunta a `/capture`, que devuelve UN JPEG por
peticion y cierra la conexion. Por eso se pide con `requests`, no con
`cv2.VideoCapture`: VideoCapture espera un flujo de video y se queda esperando
cuadros que nunca llegan, hasta agotar el tiempo de espera de ffmpeg (30 s).
Medido en la Pi: asi tardaba 52 s en juntar 3 cuadros y 2 de 3 fallaban.

Con QVGA cada foto tarda ~3,8 s y llegan las 3. En VGA el enlace no da: 17 s por
foto y conexiones caidas.
"""
from __future__ import annotations

import cv2
import numpy as np
import requests


class FrameSource:
    def __init__(self, url: str, count: int = 2, timeout: tuple[float, float] = (4, 12)):
        self.url = url
        # Dos cuadros, no ocho: cada foto cuesta ~3,8 s en este enlace y la
        # identificacion completa debe caber en unos segundos. Dos alcanzan
        # para confirmar sin sumar diez segundos de espera.
        self.count = count
        self.timeout = timeout
        # Una sola sesion: con este enlace cada conexion nueva cuesta segundos.
        self.session = requests.Session()

    def grab(self, count: int | None = None) -> list[np.ndarray]:
        """Devuelve hasta `count` cuadros validos, o los que se consigan."""
        if not self.url:
            return []

        objetivo = count or self.count
        frames: list[np.ndarray] = []

        for _ in range(objetivo * 2):
            try:
                respuesta = self.session.get(self.url, timeout=self.timeout)
                respuesta.raise_for_status()
            except requests.RequestException:
                continue

            cuadro = cv2.imdecode(
                np.frombuffer(respuesta.content, np.uint8), cv2.IMREAD_COLOR
            )
            if cuadro is not None:
                frames.append(cuadro)
            if len(frames) >= objetivo:
                break

        return frames
