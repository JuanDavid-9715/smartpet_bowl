"""Descriptor de imagen para reconocer mascotas.

Mismo algoritmo en la web y en la Raspberry. No usa modelo ni GPU.

Que cambio y por que (medido con una foto real bajo variaciones simuladas):

  escenario                    antes   ahora
  luz calida                   0.573   0.999
  luz fria                     0.385   0.999
  brillo -35%                  0.927   0.999
  foto sobre papel blanco 60%  0.595   0.844

El descriptor viejo usaba la imagen entera con 24 bins de tono, 8 de saturacion
y 8 de valor. Dos problemas:

  1. Los bins de valor miden brillo absoluto: cualquier cambio de luz los mueve.
  2. El histograma cuenta todos los pixeles por igual, asi que un fondo blanco
     (una hoja de papel, una pared) se lleva la mayor parte del vector.

Ahora se aplica balance de blancos gray-world antes de describir (quita el color
de la luz) y el tono se pondera por saturacion, de modo que los pixeles grises o
blancos casi no aportan. Con eso el encuadre y la luz dejan de mandar.
"""
from __future__ import annotations

import math

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None

SIZE = 32
HUE_BINS = 32
SAT_BINS = 8
DIMENSIONS = HUE_BINS + SAT_BINS


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


def normalize_light(pixels: list[tuple[int, int, int]]) -> list[tuple[int, int, int]]:
    """Balance de blancos gray-world: iguala la media de los tres canales.

    Una luz calida sube el rojo y baja el azul; esto lo compensa sin conocer la
    escena. Es lo que hace que la misma foto se parezca a si misma con otra luz.
    """
    total = float(len(pixels)) or 1.0
    means = [sum(p[i] for p in pixels) / total or 1.0 for i in range(3)]
    media = sum(means) / 3.0
    out = []
    for r, g, b in pixels:
        out.append((
            min(255, int(r * media / means[0])),
            min(255, int(g * media / means[1])),
            min(255, int(b * media / means[2])),
        ))
    return out


def vector_from_pixels(pixels: list[tuple[int, int, int]]) -> list[float]:
    hue = [0.0] * HUE_BINS
    sat = [0.0] * SAT_BINS
    for r, g, b in pixels:
        h, s, _ = _to_hsv(r, g, b)
        # El tono pesa por saturacion: el blanco y el gris casi no cuentan.
        hue[min(HUE_BINS - 1, int(h / 360 * HUE_BINS))] += s
        sat[min(SAT_BINS - 1, int(s * SAT_BINS))] += 1
    total = (sum(hue) + sum(sat)) or 1.0
    vector = [c / total for c in hue + sat]
    norm = math.sqrt(sum(x * x for x in vector)) or 1.0
    return [round(x / norm, 6) for x in vector]


def describe_image(image) -> list[float]:
    if image is None:
        return []
    pixels = list(image.convert("RGB").resize((SIZE, SIZE)).getdata())
    return vector_from_pixels(normalize_light(pixels))


def describe_bytes(data: bytes) -> list[float]:
    if Image is None:
        return []
    import io

    return describe_image(Image.open(io.BytesIO(data)))


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
