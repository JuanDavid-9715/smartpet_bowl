"""Camara OV2640: creacion unica y captura de cuadros."""

import time

from camera import Camera, GainCeiling

import config

_instance = None


def _setup(camara):
    """Ajustes de poca luz.

    La exposicion automatica del OV2640 ya llega a su maximo en una habitacion
    oscura; lo que la limita es el techo de ganancia, que viene bajo. Subirlo
    es lo que levanta la imagen: la media paso de 16 a 85 sobre 255.
    """
    try:
        camara.set_gainceiling(getattr(GainCeiling, config.CAMERA_GAIN))
    except (OSError, AttributeError, TypeError):
        pass
    try:
        camara.set_brightness(config.CAMERA_BRIGHTNESS)
    except (OSError, AttributeError, TypeError):
        pass


def camera():
    """Devuelve la camara ya inicializada (se crea una sola vez)."""
    global _instance
    if _instance is None:
        _instance = Camera(**config.CAMERA)
        _setup(_instance)
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
