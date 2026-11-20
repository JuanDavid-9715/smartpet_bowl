# KiCad — Esquemático eléctrico

Este proyecto usa KiCad únicamente para el esquemático eléctrico. **No se fabrica PCB ni se modelan piezas 3D.**

## Archivos

- `smartpet_bowl.kicad_sch` — esquemático del comedero, hoja única A2, **rev 8**.
- `smartpet_bowl.kicad_pro` — proyecto de KiCad.
- `sym-lib-table` — registra la biblioteca propia del proyecto.
- `libraries/smartpet_bowl.kicad_sym` — símbolos de los módulos.
- `exports/` — PDF, SVG y PNG del plano.

## Por qué hay biblioteca propia

Los módulos del comedero no son chips: son placas con regulador y borneras. KiCad
sí trae los chips pelados (`Driver_Motor:L298HN`, `Analog_ADC:HX711`,
`Sensor_Distance:VL53L1CXV0FY1`), pero usarlos aquí produciría un plano que no
corresponde al montaje y, peor, con dos errores eléctricos:

1. **El VL53L0X pelado tolera 3.6 V** en `AVDD` y `AVDDVCSEL`. El montaje es de
   5 V porque el módulo trae su regulador. Dibujar el chip con 5 V es un plano
   que quema el sensor.
2. **El riel de +5 V de todo el sistema sale del regulador del módulo L298N.**
   En el chip pelado `Vss` es una *entrada*: el plano se quedaría sin fuente de
   5 V y nadie alimentaría el ESP32.

Por eso cada módulo se dibuja como dispositivo: cuerpo con el nombre, un pin por
terminal con su nombre real (`IN1`, `DT`, `XSHUT`…) y numerado como el borne.
No son conectores genéricos con `Pin_1..16`.

| Ref | Dispositivo | Simbolo |
|---|---|---|
| U1 | Freenove ESP32-S3-WROOM CAM | propio, 40 pines en el orden del borne |
| U2 | L298N | propio, borneras del módulo |
| U3 | HX711 | propio, 4 pines al micro y 4 a la celda |
| U4 | VL53L0X | propio, 6 terminales |
| CAM1 | OV2640 (FPC) | propio, 14 señales + alimentación |
| LC1 | Celda de carga 5 kg | propio, 4 hilos |
| BZ1 | Buzzer activo | propio, 3 terminales |
| M1 | Motor del tornillo sin fin | `Motor:Motor_DC` |
| M2 | Servo SG90 | `Motor:Motor_Servo` |
| J1 | Entrada 12 V | `Connector:Barrel_Jack` |
| C1–C3 | Condensadores | `Device:C_Polarized`, `Device:C` |

## Pines del ESP32-S3 usados

| GPIO | Uso |
|---|---|
| 4, 5, 6, 7, 15, 16, 17, 18, 8, 9, 10, 11, 12, 13 | Cámara (SIOD, SIOC, VSYNC, HREF, XCLK, Y9, Y8, Y7, Y4, Y3, Y5, Y2, Y6, PCLK) |
| 14 | Servo SG90 |
| 47 | L298N IN1 |
| 48 | L298N IN2 |
| 21 | Buzzer |
| 39, 40 | HX711 SCK, DT |
| 1, 2 | VL53L0X SCL, SDA |
| 41, 42 | VL53L0X XSHUT, GPIO1 |

Los números de pin del símbolo **son los del borne físico** de la placa, así que
se pueden seguir con el cable en la mano.

**No se usa 3.3 V en ninguna parte.** El pin `3V3` de la placa y el del FPC de la
cámara van marcados como internos: los genera la placa desde 5 V y no se cablean.

**35, 36 y 37 son el PSRAM del módulo y no se cablean.** El resto de pines libres
lleva aspa (`no_connect`), que es como KiCad dice "libre a propósito".

`39` y `40` son además `SD_CLK` y `SD_DATA`: **con la celda conectada no se puede
usar la tarjeta SD**. El video va por WiFi.

`48` comparte pin con el **LED WS2812** de la placa: sirve como salida, pero el
LED puede parpadear cuando el motor cambia de estado.

## Por qué IN1 e IN2, si no hay reversa

El canal A del L298N son **dos medios puentes**, uno por cada entrada. Con
`IN1=1, IN2=0` gira en un sentido; con `IN1=0, IN2=1` gira al revés; con las dos
iguales frena. **`IN2` no puede quedar al aire**: una entrada flotante deja el
medio puente indefinido y el motor no arranca o tirita.

Si nunca se va a necesitar reversa, `IN2` se puede llevar a **GND** en vez de a
GPIO38 y el GPIO queda libre. Se pierde la reversa, que sirve para desatascar el
tornillo. El firmware actual no la usa, así que las dos opciones funcionan.

## Decisiones de diseño

- **Tapa y dosificador son mecanismos distintos.** El servo abre la tapa; el motor mueve el tornillo sin fin.
- **Tornillo sin fin en lugar de compuerta.** Mueve un volumen casi constante por vuelta, no depende de la gravedad y no atasca croquetas irregulares.
- **El lazo lo cierra la celda de carga.** El motor gira y la báscula decide cuándo parar. Por eso `ENA` queda con el jumper a 5 V.
- **Solo el canal A del L298N.** Quedan libres IN3, IN4, ENB, OUT3 y OUT4.
- **C1 en 12 V y C2 en 5 V** absorben los picos del motor y del servo para que el ESP32 no se reinicie.
- **El ESP32-S3 no decide nada.** Recibe comandos, mueve servo y motor, pesa y reporta.

## Alimentación

**Los 5 V salen del USB del PC**, por el pin `+5V` de la placa. De ahí comen el
ESP32, el HX711, el VL53L0X, el buzzer y la lógica del L298N. El riel de 12 V es
aparte y solo alimenta el puente H.

Consecuencia: **hay que quitar el jumper `5V-EN` del L298N.** Con el jumper
puesto, el borne `+5V` es la *salida* del regulador del módulo; si además está
conectado al riel del USB, dos reguladores pelean y uno pierde. Sin jumper, ese
borne es una entrada y el módulo toma los 5 V del USB.

## Avisos eléctricos

- **Un GPIO del ESP32 no tolera 5 V.** El máximo absoluto del datasheet es
  **3.6 V** (`Allowed input voltage 0.3–3.6 V`, tabla 5.1). Solo el pin `+5V`
  de la placa está hecho para 5 V. Que un GPIO aguante 5 V un rato no significa
  que esté dentro de especificación: el diodo de protección conduce y el daño se
  acumula.
- **HX711 a 5 V**: su salida `DT` llega a 5 V y GPIO40 no admite más de 3.6 V.
  El plano muestra la conexión **directa**, sin divisor, porque es lo que está
  montado. Queda fuera de especificación del pin: el diodo de protección del
  ESP32 conduce. Con R1 = 10 kΩ y R2 = 20 kΩ en divisor `DT` bajaría a 3.33 V.
  Está anotado en la hoja para que la desviación no pase desapercibida.
- **Servo**: el SG90 consume 220 mA en movimiento y **650 mA en bloqueo**. Un
  puerto USB 2.0 entrega 500 mA y el ESP32 con WiFi ya pide ~250 mA. Si la placa
  se reinicia al mover el servo, ese es el motivo: hay que darle al servo su
  propia fuente de 5 V con GND común.
- **No conectar el USB y el borne de 5 V de otra fuente al mismo tiempo**, salvo
  que esa fuente sea la única y el USB solo esté para datos.

## Regenerar los planos

```bash
kicad-cli sch export svg --output /tmp/plano hardware/kicad/smartpet_bowl.kicad_sch
kicad-cli sch export pdf --output /tmp/plano/smartpet_bowl.pdf hardware/kicad/smartpet_bowl.kicad_sch
```

## Verificación eléctrica

`kicad-cli sch erc` reporta **0 infracciones**.

En el camino aparecieron y se corrigieron: la celda conectada a etiquetas sin par
(rev 3), pines del ESP32 sin correspondencia, y en la rev 5 un GND etiquetado por
error sobre `OUT2` y sobre `+12V`, que el ERC detectó como corto entre `+12V` y
`GND`.

Cada señal tiene exactamente dos extremos: un pin del ESP32 y un terminal del
módulo. Las redes `GND` (12), `+5V` (8) y `+12V` (3) son las únicas con más de
dos puntos.

Antes de llevar esto a una placa real habría que asignar footprints.
