"""Decision del reconocedor: cuantas coincidencias bastan.

El 20 de noviembre, sin nada frente a la camara, el servicio "identifico" a Armi
con 11 coincidencias y ordeno servir 204 g. El umbral estaba en 10. Estas
pruebas fijan el piso para que no vuelva a pasar.
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from src import features as vision  # noqa: E402
from src.recognizer import PetRecognizer  # noqa: E402


def _nombre_de(perfil, rec: PetRecognizer) -> str:
    for nombre, guardado in rec._profiles.items():
        if guardado is perfil:
            return nombre
    raise AssertionError("perfil desconocido")


def _con_puntajes(monkeypatch, puntajes: dict[str, int]) -> PetRecognizer:
    """Reconocedor cuyos puntajes contra cada mascota son fijos.

    Asi se prueba la decision sin depender de imagenes reales.
    """
    rec = PetRecognizer()
    rec._profiles = {nombre: np.zeros((10, 32), dtype=np.uint8) for nombre in puntajes}

    monkeypatch.setattr(
        "src.recognizer.vision.descriptors",
        lambda frame: np.zeros((10, 32), dtype=np.uint8),
    )
    monkeypatch.setattr(
        "src.recognizer.vision.match_score",
        lambda perfil, puntos: puntajes[_nombre_de(perfil, rec)],
    )
    return rec


def test_rechaza_pocas_coincidencias(monkeypatch):
    """11 coincidencias no identifican a nadie, aunque dominen 11 contra 3."""
    rec = _con_puntajes(monkeypatch, {"Armi": 11, "Jiru": 3})

    mascota, confianza = rec.identify([np.zeros((4, 4, 3), dtype=np.uint8)])

    assert mascota is None
    assert confianza == 0.0


def test_acepta_coincidencias_suficientes(monkeypatch):
    """Sesenta coincidencias si identifican: es lo que da una toma real."""
    rec = _con_puntajes(monkeypatch, {"Armi": 60, "Jiru": 24})

    mascota, confianza = rec.identify([np.zeros((4, 4, 3), dtype=np.uint8)])

    assert mascota == "Armi"
    assert confianza == round(60 / 84, 3)


def test_el_umbral_tiene_margen():
    """El piso debe quedar entre un falso positivo y una toma buena."""
    assert 11 < vision.MIN_MATCHES < 60
