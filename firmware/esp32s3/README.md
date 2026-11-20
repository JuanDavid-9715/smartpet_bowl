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

## Placa y cableado real

**Freenove ESP32-S3-WROOM CAM** (ESP32-S3-WROOM-1). El pinout de camara se
verifico contra la documentacion oficial de Freenove.

| GPIO | Conectado a | Estado |
|---|---|---|
| 4 | Camara SIOD | ok |
| 5 | Camara SIOC | ok |
| 6 | Camara VSYNC | ok |
| 7 | Camara HREF | ok |
| 8, 9, 10, 11, 12, 13 | Camara Y4, Y3, Y5, Y2, Y6, PCLK | ok |
| 15 | Camara XCLK | ok |
| 16, 17, 18 | Camara Y9, Y8, Y7 | ok |
| 14 | L298N IN1 | ok |
| **38** | **L298N IN2** | **FALTA CABLEAR** |
| 21 | Buzzer I/O | ok |
| 47 | Servo SG90 PWM | ok |
| 39 | HX711 SCK | ok |
| 40 | HX711 DT | ok |
| 1 | VL53L0X SCL | ok |
| 2 | VL53L0X SDA | ok |
| 41 | VL53L0X XSHUT | ok (debe ir en alto) |
| 42 | VL53L0X GPIO1 | ok (no se usa) |
| 35, 36, 37 | PSRAM interno | **PROHIBIDO USAR** |

**38, 39 y 40 son tambien SD_CMD, SD_CLK y SD_DATA** en esta placa. Como el motor
y la celda de carga los usan, **no se puede insertar la tarjeta SD** al mismo
tiempo: el bus se comparte y el pesaje se corrompe. La captura de video va por
WiFi, no hace falta la SD.

**ENA del L298N: puenteado a 5 V con el jumper.** Asi el motor gira a tope y no
hace falta un GPIO. La dosificacion la controla la celda de carga, no la
velocidad. Si mas adelante quieres regular velocidad, cambia `PIN_MOTOR_ENA`
de `-1` a un GPIO libre y quita el jumper.

## Antes de compilar

Edita `include/config.h`:

- `WIFI_SSID`, `WIFI_PASS`, `MQTT_HOST`, `FEEDER_CODE`.
- `scale.set_scale(-430.0)` en `main.cpp` es un valor inicial. **Se calibra en el montaje** con un peso conocido.
- `PRESENCIA_MM` (700) y `PRESENCIA_MS` (1500) se ajustan segun donde quede el sensor.
- El servo es un **SG90**, no el MG996R del diseno. Si no levanta la tapa, hay que volver al MG996R.

## Avisos electricos

- **HX711 alimentado a 5 V**: su salida DT queda a 5 V y el ESP32 tolera 3.6 V.
  Alimenta el HX711 a **3.3 V** o pon un divisor en DT.
- **VL53L0X a 5 V**: solo seguro si el modulo trae regulador (GY-VL53L0XV2 lo trae).
- **Servo y motor con fuente aparte**: el SG90 pide ~700 mA de pico y el motor
  mas. La salida de 5 V del L298N no alcanza para el ESP32 con esa carga.

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
