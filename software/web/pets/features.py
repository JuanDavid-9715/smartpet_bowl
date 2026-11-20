"""Deteccion del animal y puntos caracteristicos (ORB).

Mismo codigo en la web y en la Raspberry. Aqui se decide dos cosas:

1. **Donde esta el animal**: un detector YOLO11n preentrenado (COCO) recorta el
   gato o el perro del cuadro. Asi el papel de la hoja, la mesa o la pared no
   entran en la comparacion.
2. **Como se compara**: con puntos caracteristicos ORB, no con color. Medido:
   la misma foto da 329 coincidencias consigo misma y 9 con otra mascota; y
   aguanta cambios de luz (+-40 %) y de distancia hasta un 30 %.

El histograma de color se descarto para identificar: gato y perro se parecian
0.909, suficiente para confundirlos con cualquier umbral razonable.
"""
from __future__ import annotations

import base64
import os

import cv2
import numpy as np

COCO_CAT = 15
COCO_DOG = 16
ANIMAL_CLASSES = (COCO_CAT, COCO_DOG)

ORB_FEATURES = 300
GOOD_MATCH_DISTANCE = 50
# Dos mascotas distintas dan menos de 10 coincidencias; la correcta pasa de 100.
MIN_MATCHES = 15

_MODEL_CACHE = {}


def _model_path():
    # pets/vision.py -> <proyecto>/models/ ; src/vision.py -> <proyecto>/models/
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(raiz, "models", "yolo11n.onnx")


def _detector(path=None):
    """Carga el detector una sola vez. Si falta el modelo, devuelve None."""
    path = path or _model_path()
    if path in _MODEL_CACHE:
        return _MODEL_CACHE[path]
    net = None
    if os.path.exists(path):
        try:
            net = cv2.dnn.readNetFromONNX(path)
        except Exception:  # noqa: BLE001 - sin modelo se sigue sin recorte
            net = None
    _MODEL_CACHE[path] = net
    return net


def crop_animal(bgr, confidence=0.30):
    """Devuelve el recorte del animal detectado, o la imagen completa."""
    net = _detector()
    if net is None:
        return bgr

    alto, ancho = bgr.shape[:2]
    blob = cv2.dnn.blobFromImage(bgr, 1 / 255.0, (640, 640), swapRB=True, crop=False)
    net.setInput(blob)
    salida = net.forward()[0].T

    cajas, confianzas = [], []
    for fila in salida:
        clase = int(np.argmax(fila[4:]))
        score = float(fila[4 + clase])
        if score < confidence or clase not in ANIMAL_CLASSES:
            continue
        cx, cy, bw, bh = fila[:4]
        cajas.append([
            float((cx - bw / 2) * ancho / 640),
            float((cy - bh / 2) * alto / 640),
            float(bw * ancho / 640),
            float(bh * alto / 640),
        ])
        confianzas.append(score)

    if not cajas:
        return bgr

    indices = np.array(cv2.dnn.NMSBoxes(cajas, confianzas, confidence, 0.45)).flatten()
    x, y, cw, ch = cajas[int(indices[0])]
    x1, y1 = max(0, int(x)), max(0, int(y))
    x2, y2 = min(ancho, int(x + cw)), min(alto, int(y + ch))
    if x2 - x1 < 8 or y2 - y1 < 8:
        return bgr
    return bgr[y1:y2, x1:x2]


def descriptors(bgr):
    """Puntos caracteristicos del animal. Devuelve ndarray (N,32) uint8 o None."""
    recorte = crop_animal(bgr)
    gris = cv2.cvtColor(recorte, cv2.COLOR_BGR2GRAY)
    gris = cv2.equalizeHist(gris)
    orb = cv2.ORB_create(nfeatures=ORB_FEATURES)
    _, des = orb.detectAndCompute(gris, None)
    return des


def encode(des) -> str:
    """Serializa para la base y para la API: '<cantidad>:<base64>'."""
    if des is None or len(des) == 0:
        return ""
    crudo = np.ascontiguousarray(des, dtype=np.uint8).tobytes()
    return "%d:%s" % (len(des), base64.b64encode(crudo).decode())


def decode(texto) -> np.ndarray | None:
    if not texto or ":" not in texto:
        return None
    cantidad, _, datos = texto.partition(":")
    try:
        crudo = base64.b64decode(datos)
        return np.frombuffer(crudo, dtype=np.uint8).reshape(int(cantidad), 32)
    except (ValueError, TypeError):
        return None


def combine(blobs) -> str:
    """Une los descriptores de varias fotos en un solo texto."""
    partes = [d for d in (decode(t) for t in blobs) if d is not None and len(d)]
    if not partes:
        return ""
    return encode(np.vstack(partes))


def match_score(des_a, des_b) -> int:
    """Cuantos puntos coinciden de verdad entre dos conjuntos de descriptores."""
    if des_a is None or des_b is None or len(des_a) == 0 or len(des_b) == 0:
        return 0
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    pares = matcher.match(des_a, des_b)
    return sum(1 for par in pares if par.distance < GOOD_MATCH_DISTANCE)


def decode_bgr(datos: bytes):
    """Bytes de una imagen (JPEG/PNG) al formato que usa OpenCV."""
    arreglo = np.frombuffer(datos, dtype=np.uint8)
    return cv2.imdecode(arreglo, cv2.IMREAD_COLOR)


def from_ndarray(rgb) -> np.ndarray:
    """Convierte un arreglo RGB (PIL) al BGR de OpenCV sin cambiar el orden."""
    return cv2.cvtColor(np.ascontiguousarray(rgb), cv2.COLOR_RGB2BGR)


def similarity_label(puntaje: int) -> str:
    if puntaje >= 100:
        return "muy alta"
    if puntaje >= MIN_MATCHES * 2:
        return "alta"
    if puntaje >= MIN_MATCHES:
        return "suficiente"
    return "baja"
