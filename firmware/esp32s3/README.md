# Firmware del comedero — ESP32-S3

## Estado

**Escrito y revisado, pero NO compilado.** En esta maquina solo esta el core AVR de Arduino; el core de ESP32-S3 no esta instalado, asi que no se pudo verificar la compilacion. La primera compilacion real se hace en el montaje.

## Que hace

1. A la hora programada, la Raspberry pide `llamada {mascota, gramos, segundos}`.
2. El dosificador sirve la racion con la **tapa cerrada**, con lazo cerrado sobre la celda de carga.
3. Suena el buzzer y se **abre la tapa** para que la mascota se acerque.
4. El sensor de distancia detecta presencia y publica `evento/presencia`.
5. La Raspberry identifica y responde `servir` o `cerrar`.
6. Al cerrar la ventana se pesa el sobrante y se publica `evento/sobrante`.

## Topics

| Direccion | Topic | Carga |
|---|---|---|
| ESP32 → Pi | `comedero/{id}/evento/presencia` | `{distancia_mm}` |
| ESP32 → Pi | `comedero/{id}/evento/peso` | `{gramos}` |
| ESP32 → Pi | `comedero/{id}/evento/sobrante` | `{gramos, mascota, duracion_s}` |
| ESP32 → Pi | `comedero/{id}/estado` | `{en_linea, version, estado}`, retenido |
| Pi → ESP32 | `comedero/{id}/comando/llamada` | `{mascota, gramos, segundos}` |
| Pi → ESP32 | `comedero/{id}/comando/servir` | `{mascota}` |
| Pi → ESP32 | `comedero/{id}/comando/cerrar` | `{motivo}` |
| Pi → ESP32 | `comedero/{id}/comando/reiniciar` | `{motivo}` |

## Video

El ESP32 sirve MJPEG por HTTP en el puerto **81**:

- `http://<ip-del-comedero>:81/capture` — un cuadro.
- `http://<ip-del-comedero>:81/stream` — el mismo manejador, cuadro a cuadro.

La Raspberry se conecta cuando hay presencia. Es **pull**, no push: el ESP32 no necesita conocer la IP de la Pi.

## Antes de compilar

Edita `include/config.h`:

- `WIFI_SSID`, `WIFI_PASS`, `MQTT_HOST`, `FEEDER_CODE`.
- **Los pines de la camara dependen de la placa.** Los de `config.h` son de referencia; verifica contra el pinout de tu modulo ESP32-S3.
- `scale.set_scale(-430.0)` en `main.cpp` es un valor inicial. **Se calibra en el montaje** con un peso conocido.
- `PRESENCIA_MM` (700) y `PRESENCIA_MS` (1500) se ajustan segun donde quede el sensor.

## Compilar y subir

```bash
pio run
pio run -t upload
pio device monitor
```

## Lo que falta verificar en el montaje

- Calibracion de la celda de carga y deriva con la temperatura.
- Que el L298N entregue par suficiente a 5 V; si no, subir el bloque de potencia a 9-12 V.
- Que el dosificador no atasque croquetas irregulares.
- Que el servo abra y cierre sin forzar.
- Que el stream MJPEG llegue fluido a la Raspberry.
