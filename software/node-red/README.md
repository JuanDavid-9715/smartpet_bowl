# Node-RED — orquestador MQTT y tablero

Node-RED vigila el comedero por MQTT y ofrece un tablero para verlo y mandarle
órdenes. **No hace reconocimiento**: eso vive en la Raspberry (`software/raspberry-pi`),
y los datos de negocio (mascotas, historial, alertas) viven en el Django
(`software/web`). Aquí solo se orquesta y se opera.

## Qué hace

| Bloque | Función |
|---|---|
| `evento/#` | Registra peso, presencia y sobrante que publica la placa |
| `ip` | Guarda la IP del comedor (la placa la publica retenida) |
| `estado` | Sabe si el servicio de la Raspberry está en línea |
| `GET /comedero` | Tablero: estado, órdenes y últimos 12 eventos |
| `GET /comedero/estado` | El mismo estado en JSON (lo consulta el tablero cada 2 s) |
| `POST /comedero/comando` | Manda una orden a la placa |

## Órdenes aceptadas

El tablero solo deja pasar las que entiende el firmware (`firmware/esp32s3-micropython/mqtt.py`):

| Acción | Efecto en la placa | Cuerpo |
|---|---|---|
| `servir` | Abre la tapa | `{"accion": "servir"}` |
| `cerrar` | Para el motor y cierra la tapa | `{"accion": "cerrar"}` |
| `reiniciar` | Reinicia la placa | `{"accion": "reiniciar"}` |
| `llamada` | Dosifica gramos, abre y toca el nombre | `{"accion": "llamada", "mascota": "Jiru", "gramos": 60}` |

Una acción desconocida o una `llamada` sin mascota o sin gramos responde **400**
con el motivo; una orden válida responde **200**.

## Topics

```text
comedero/SPB-42/evento/peso        {"gramos": 62.5}        placa -> Node-RED
comedero/SPB-42/evento/presencia   {"distancia_mm": 310}   placa -> Node-RED
comedero/SPB-42/evento/sobrante    {...}                   placa -> Node-RED
comedero/SPB-42/ip                 {"ip": "10.204.126.11"} placa -> Node-RED (retenido)
comedero/SPB-42/estado             {"en_linea": true}      Pi    -> Node-RED (retenido)
comedero/SPB-42/comando/<accion>   {...}                   Node-RED -> placa
```

## Archivos

```text
software/node-red/
├── panel.html      Tablero (HTML, CSS y JS en un solo archivo, sin dependencias)
├── build_flows.py  Incrusta panel.html en flows.json
├── flows.json      Flujo generado (no se edita a mano)
├── settings.js     Configuración; el tablero se sirve en /comedero y el editor en /red
└── README.md
```

`flows.json` se genera: si cambias `panel.html`, vuelve a ejecutar

```bash
python3 software/node-red/build_flows.py
```

## Cómo se arranca

En la Raspberry lo levanta `software/raspberry-pi/start.sh` al encender, con su
carpeta de usuario dentro del proyecto:

```bash
setsid node-red --userDir <proyecto>/node-red
```

Así Node-RED no escribe en `~/.node-red` y todo el trabajo queda dentro de la
carpeta del proyecto.

A mano, para desarrollo:

```bash
make node-red
```

## Detalle que costó encontrar

El nodo `http response` calcula el código así:

```js
var statusCode = node.statusCode || parseInt(msg.statusCode) || 200;
```

Por eso una propiedad `statusCode: "200"` en el nodo gana siempre y el `400` que
ponga una función se pierde. La propiedad va **vacía** en el nodo de la respuesta
de comandos, y el código lo pone la función.

## Lo que este tablero no hace

- No muestra video: el MJPEG está en el panel técnico del Django
  (`/app/eventos/`), que solo existe en la Raspberry.
- No guarda historial ni alertas: eso es del Django (`/app/mascotas/`).
- No identifica mascotas: eso lo hace el servicio de la Raspberry con ORB.
