import io
import sys
from pathlib import Path

import pytest
from PIL import Image

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from src import descriptor  # noqa: E402

WEB = HERE.parent / "web"


def _jpeg(color) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (48, 48), color).save(buffer, "JPEG")
    return buffer.getvalue()


def test_dimension_del_vector():
    vector = descriptor.describe_bytes(_jpeg((180, 140, 90)))
    assert len(vector) == descriptor.DIMENSIONS == 40


def test_vector_normalizado():
    vector = descriptor.describe_bytes(_jpeg((20, 120, 200)))
    norma = sum(x * x for x in vector) ** 0.5
    assert norma == pytest.approx(1.0, abs=0.01)


def test_misma_imagen_mismo_vector():
    data = _jpeg((120, 90, 60))
    assert descriptor.describe_bytes(data) == descriptor.describe_bytes(data)


def test_centroide_de_vectores_iguales():
    vector = descriptor.describe_bytes(_jpeg((90, 90, 90)))
    centro = descriptor.centroid([vector, vector])
    assert descriptor.similarity(centro, vector) > 0.99


def test_paridad_con_la_web():
    """El vector guardado por la web debe coincidir con el que calcula la Pi."""
    import importlib.util

    ruta = WEB / "pets" / "embedding.py"
    if not ruta.exists():
        pytest.skip("no esta el proyecto web al lado")
    spec = importlib.util.spec_from_file_location("web_embedding", ruta)
    web = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(web)

    data = _jpeg((170, 130, 80))
    assert web.DIMENSIONS == descriptor.DIMENSIONS
    assert web.describe_bytes(data) == descriptor.describe_bytes(data)
