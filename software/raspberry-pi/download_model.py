"""Descarga el modelo de vision una sola vez.

Sin API externa en tiempo de ejecucion y sin entrenamiento: la red se usa
congelada como extractora de caracteristicas.
"""
import hashlib
import sys
import urllib.request
from pathlib import Path

URL = "https://github.com/onnx/models/raw/main/validated/vision/classification/mobilenet/model/mobilenetv2-7.onnx"
TARGET = Path(__file__).resolve().parent / "models" / "mobilenetv3.onnx"


def main() -> int:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    if TARGET.exists():
        print(f"Ya existe: {TARGET} ({TARGET.stat().st_size} bytes)")
        return 0
    print(f"Descargando {URL}")
    try:
        urllib.request.urlretrieve(URL, TARGET)
    except Exception as exc:
        print(f"No se pudo descargar: {exc}")
        print("Sin modelo, el servicio usa el descriptor de color como respaldo.")
        return 1
    digest = hashlib.sha256(TARGET.read_bytes()).hexdigest()
    print(f"Listo: {TARGET} ({TARGET.stat().st_size} bytes)")
    print(f"sha256: {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
