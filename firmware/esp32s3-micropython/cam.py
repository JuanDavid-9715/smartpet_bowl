"""Camara OV2640: creacion unica y captura de cuadros."""

import time

from camera import Camera

import config

_instance = None


def camera():
    """Devuelve la camara ya inicializada (se crea una sola vez)."""
    global _instance
    if _instance is None:
        _instance = Camera(**config.CAMERA)
    return _instance


def frame(cam, retries=3):
    """Captura un cuadro. Hay que liberarlo con cam.free_buffer()."""
    for _ in range(retries):
        try:
            buf = cam.capture()
        except OSError:
            buf = None
        if buf is not None:
            return buf
        time.sleep_ms(20)
    raise OSError("camara: sin cuadro disponible")


def info(cam):
    return {
        "sensor": cam.sensor_name,
        "width": cam.get_pixel_width(),
        "height": cam.get_pixel_height(),
        "format": cam.get_pixel_format(),
    }
