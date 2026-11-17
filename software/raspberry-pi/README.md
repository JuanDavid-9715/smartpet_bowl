# Servicio de la Raspberry Pi 4

## Que hace

Recibe los eventos del comedero por MQTT, identifica a la mascota con vision,
ordena servir la racion, mide el sobrante, guarda en el Django local y
sincroniza a la nube.

## Piezas

| Archivo | Responsabilidad |
|---|---|
| `main.py` | Punto de entrada. `--check` valida configuracion sin conectar nada |
| `src/config.py` | Variables de entorno |
| `src/client.py` | Cliente MQTT (publish/subscribe) |
| `src/vision.py` | Captura del MJPEG y extraccion de caracteristicas |
| `src/recognizer.py` | Compara con las fotos de referencia de cada mascota |
| `src/feeding.py` | Raciones, sobrantes y clasificacion de la comida |
| `src/storage.py` | Guardado local y cola de sincronizacion con reintentos |
| `src/service.py` | Orquestacion y horarios |

## Instalacion

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env    # edita host MQTT, token y URL del stream
python download_model.py   # opcional: sin el, usa descriptor de color
```

En la Raspberry usa `opencv-python-headless` para no arrastrar interfaz grafica.

## Uso

```bash
.venv/bin/python main.py --check   # verifica configuracion y raciones
.venv/bin/python main.py           # arranca el servicio
```

## Vision

- El modelo se descarga una vez y vive en `models/`. **No se entrena nada y no se llama a ninguna API.**
- Si el modelo falta, cae automaticamente a un descriptor de color HSV, que separa sin problema un gato atigrado de un boxer.
- Para distinguir dos gatos del mismo color haria falta un modelo de re-identificacion de mascotas: fuera del alcance de este proyecto.

Las fotos de referencia van en `photos/<NombreDeLaMascota>/*.jpg`. Deben ser las mismas que sube la persona en la web: la mascota frente al plato, de frente, comiendo y desde arriba.

## Pruebas

```bash
python -m pytest tests -q
```

## Pendiente de verificar en el montaje

- Que el stream MJPEG del ESP32 llegue estable.
- Que la identificacion acierte con las fotos impresas.
- El consumo: OpenCV, Django, Mosquitto y Node-RED conviven en la misma Pi 4.
