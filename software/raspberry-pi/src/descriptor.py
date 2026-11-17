"""Descriptor de imagen identico al de la web.

Misma matematica que software/web/pets/embedding.py: histograma HSV normalizado
sobre una miniatura de 32x32. Asi el vector que guarda la web al registrar a la
mascota se puede comparar con un cuadro de la camara sin recalcular nada.
Si se cambia por una red neuronal, hay que recalcular los vectores guardados.
"""
from __future__ import annotations

import io
import math

import numpy as np
from PIL import Image

SIZE = 32
HUE_BINS = 24
SAT_BINS = 8
VAL_BINS = 8
DIMENSIONS = HUE_BINS + SAT_BINS + VAL_BINS


def _describe(image: Image.Image) -> list[float]:
    image = image.convert("RGB").resize((SIZE, SIZE))
    hue = [0.0] * HUE_BINS
    sat = [0.0] * SAT_BINS
    val = [0.0] * VAL_BINS
    pixels = list(image.getdata())
    for r, g, b in pixels:
        rn, gn, bn = r / 255.0, g / 255.0, b / 255.0
        hi, lo = max(rn, gn, bn), min(rn, gn, bn)
        delta = hi - lo
        if delta == 0:
            h = 0.0
        elif hi == rn:
            h = (60 * ((gn - bn) / delta)) % 360
        elif hi == gn:
            h = 60 * ((bn - rn) / delta) + 120
        else:
            h = 60 * ((rn - gn) / delta) + 240
        s = 0.0 if hi == 0 else delta / hi
        hue[min(HUE_BINS - 1, int(h / 360 * HUE_BINS))] += 1
        sat[min(SAT_BINS - 1, int(s * SAT_BINS))] += 1
        val[min(VAL_BINS - 1, int(hi * VAL_BINS))] += 1
    total = float(len(pixels)) or 1.0
    vector = [c / total for c in hue + sat + val]
    norm = math.sqrt(sum(x * x for x in vector)) or 1.0
    return [round(x / norm, 6) for x in vector]


def describe_bytes(data: bytes) -> list[float]:
    return _describe(Image.open(io.BytesIO(data)))


def describe_array(frame_bgr: np.ndarray) -> list[float]:
    rgb = frame_bgr[:, :, ::-1]
    return _describe(Image.fromarray(np.ascontiguousarray(rgb)))


def centroid(vectors: list[list[float]]) -> list[float]:
    usable = [v for v in vectors if v and len(v) == DIMENSIONS]
    if not usable:
        return []
    summed = [sum(column) for column in zip(*usable)]
    norm = math.sqrt(sum(x * x for x in summed)) or 1.0
    return [round(x / norm, 6) for x in summed]


def similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return round(sum(x * y for x, y in zip(a, b)), 4)
