"""Descriptor de imagen para reconocer mascotas.

Mismo algoritmo en la web y en la Raspberry: histograma HSV normalizado sobre
una miniatura. No necesita modelo ni GPU y es determinista, asi que el vector
guardado al registrar la mascota se puede comparar despues con un cuadro de la
camara. Si mas adelante se cambia por una red neuronal, solo cambia esta funcion.
"""
from __future__ import annotations

import math

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None

SIZE = 32
HUE_BINS = 24
SAT_BINS = 8
VAL_BINS = 8
DIMENSIONS = HUE_BINS + SAT_BINS + VAL_BINS


def _to_hsv(r: int, g: int, b: int) -> tuple[float, float, float]:
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    hi, lo = max(r, g, b), min(r, g, b)
    delta = hi - lo
    if delta == 0:
        h = 0.0
    elif hi == r:
        h = (60 * ((g - b) / delta)) % 360
    elif hi == g:
        h = 60 * ((b - r) / delta) + 120
    else:
        h = 60 * ((r - g) / delta) + 240
    s = 0.0 if hi == 0 else delta / hi
    return h, s, hi


def describe_bytes(data: bytes) -> list[float]:
    if Image is None:
        return []
    import io

    image = Image.open(io.BytesIO(data)).convert("RGB").resize((SIZE, SIZE))
    hue = [0.0] * HUE_BINS
    sat = [0.0] * SAT_BINS
    val = [0.0] * VAL_BINS
    pixels = list(image.getdata())
    for r, g, b in pixels:
        h, s, v = _to_hsv(r, g, b)
        hue[min(HUE_BINS - 1, int(h / 360 * HUE_BINS))] += 1
        sat[min(SAT_BINS - 1, int(s * SAT_BINS))] += 1
        val[min(VAL_BINS - 1, int(v * VAL_BINS))] += 1
    total = float(len(pixels)) or 1.0
    vector = [c / total for c in hue + sat + val]
    norm = math.sqrt(sum(x * x for x in vector)) or 1.0
    return [round(x / norm, 6) for x in vector]


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
