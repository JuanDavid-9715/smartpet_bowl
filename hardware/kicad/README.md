# KiCad — Esquemático eléctrico

Este proyecto usa KiCad únicamente para el esquemático eléctrico. **No se fabrica PCB ni se modelan piezas 3D.**

## Archivos

- `smartpet_bowl.kicad_sch` — esquemático del comedero, hoja única A2, **rev 5**.
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
| 14 | L298N IN1 |
| 38 | L298N IN2 |
| 21 | Buzzer |
| 47 | Servo SG90 |
| 39, 40 | HX711 SCK, DT |
| 1, 2 | VL53L0X SCL, SDA |
| 41, 42 | VL53L0X XSHUT, GPIO1 |

Los números de pin del símbolo **son los del borne físico** de la placa, así que
se pueden seguir con el cable en la mano.

**No se usa 3.3 V en ninguna parte.** El pin `3V3` de la placa y el del FPC de la
cámara van marcados como internos: los genera la placa desde 5 V y no se cablean.

**35, 36 y 37 son el PSRAM del módulo y no se cablean.** El resto de pines libres
lleva aspa (`no_connect`), que es como KiCad dice "libre a propósito".

`38`, `39` y `40` son además `SD_CMD`, `SD_CLK` y `SD_DATA`: **con la celda y el
motor conectados no se puede usar la tarjeta SD**. El video va por WiFi.

## Decisiones de diseño

- **Tapa y dosificador son mecanismos distintos.** El servo abre la tapa; el motor mueve el tornillo sin fin.
- **Tornillo sin fin en lugar de compuerta.** Mueve un volumen casi constante por vuelta, no depende de la gravedad y no atasca croquetas irregulares.
- **El lazo lo cierra la celda de carga.** El motor gira y la báscula decide cuándo parar. Por eso `ENA` queda con el jumper a 5 V.
- **Solo el canal A del L298N.** Quedan libres IN3, IN4, ENB, OUT3 y OUT4.
- **C1 en 12 V y C2 en 5 V** absorben los picos del motor y del servo para que el ESP32 no se reinicie.
- **El ESP32-S3 no decide nada.** Recibe comandos, mueve servo y motor, pesa y reporta.

## Avisos eléctricos

- **HX711 a 5 V**: su salida `DT` llega a 5 V y GPIO40 tolera 3.6 V. Hace falta un divisor o alimentar el módulo a 3.3 V (esto último ya no es posible sin ese riel).
- **Servo y motor**: el SG90 pide ~700 mA de pico. La salida de 5 V del L298N no debería alimentar además al ESP32 con esa carga; conviene una fuente aparte.
- **No conectar el USB del ESP32 y el 5 V del L298N al mismo tiempo.**

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
