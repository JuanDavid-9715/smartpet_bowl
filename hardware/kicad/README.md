# KiCad — Esquemático eléctrico

Este proyecto usa KiCad únicamente para el esquemático eléctrico. **No se fabrica PCB ni se modelan piezas 3D.**

## Archivos

- `smartpet_bowl.kicad_sch` — esquemático del comedero, hoja única A2, **rev 4**.
- `exports/smartpet_bowl.pdf` — plano para imprimir o anexar al documento.
- `exports/smartpet_bowl.svg` — plano vectorial para presentaciones.
- `exports/smartpet_bowl.png` — imagen del plano para el informe.

## Qué representa

El comedero se arma con **módulos comprados** unidos por cables, no con componentes soldados. Por eso el plano es de conectores y nets: cada módulo aparece con los terminales que tiene físicamente.

La fuente del pinout es el **PDF oficial de Freenove** (`Datasheet/ESP32-S3 Pinout.pdf`), no una tabla de memoria. Los 40 pines de la placa están en el orden real de los dos bornes.

| Ref | Módulo | Nets |
|---|---|---|
| U1 | Freenove ESP32-S3-WROOM CAM (2×20) | ver tabla de pines |
| J1 | Cámara OV2640 (FPC) | `GPIO4`–`GPIO18`, `+3V3`, `GND` |
| J2 | L298N | `GPIO14`, `GPIO38`, `+12V`, `+5V`, `GND`, `MOTOR_A`, `MOTOR_B` |
| M1 | Motor DC del tornillo sin fin | `MOTOR_A`, `MOTOR_B` |
| J3 | Servo SG90 de la tapa | `GPIO47`, `+5V`, `GND` |
| J4 | Módulo buzzer activo | `GPIO21`, `+5V`, `GND` |
| J5 | HX711 | `+3V3`, `GPIO40`, `GPIO39`, `GND`, `LC_E±`, `LC_A±` |
| J6 | Celda de carga 5 kg | `LC_E+`, `LC_E-`, `LC_A-`, `LC_A+` |
| J7 | VL53L0X | `+5V`, `GND`, `GPIO1`, `GPIO2`, `GPIO42`, `GPIO41` |
| J8 | Fuente 12 V | `+12V`, `GND` |
| C1 | 1000 µF 25 V | `+12V`, `GND` |
| C2 | 470 µF 16 V | `+5V`, `GND` |
| C3–C5 | 100 nF | `+3V3`, `+5V`, `GND` |

### Pines del ESP32-S3 usados

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

**35, 36 y 37 son el PSRAM del módulo y no se cablean.** El resto queda libre y marcado con aspa (`no_connect`), que es como KiCad dice "libre a propósito".

`38`, `39` y `40` son además `SD_CMD`, `SD_CLK` y `SD_DATA` en esta placa: **con la celda de carga y el motor conectados no se puede usar la tarjeta SD**. El video va por WiFi, así que no hace falta.

## Decisiones de diseño

- **Tapa y dosificador son mecanismos distintos.** El servo abre la tapa; el motor DC mueve un tornillo sin fin que dosifica. Una sola compuerta no puede hacer las dos cosas: si queda abierta, la comida cae libre y se pierde el control de porción.
- **Tornillo sin fin en lugar de compuerta estranguladora.** El tornillo mueve un volumen casi constante por vuelta y no depende de la gravedad ni del nivel del depósito. Una compuerta por gravedad atasca croquetas irregulares y su caudal cambia con la humedad.
- **El lazo lo cierra la celda de carga, no el motor.** El motor gira y la celda decide cuándo parar, así que la precisión viene de la báscula. Por eso ENA queda con el jumper a 5 V: no hace falta regular velocidad.
- **Solo el canal A del L298N.** El motor es uno solo, así que IN3, IN4, OUT3 y OUT4 quedan libres.
- **El servo va a 5 V con condensador.** El SG90 pide picos de ~700 mA; C2 absorbe ese pico para que el ESP32 no se reinicie.
- **Buzzer activo al GPIO, sin resistencia ni amplificador.** Es un módulo con transistor: consume pocos miliamperios de la señal y no necesita etapa de potencia. Se descartó el MAX98357A por no sumar componentes.
- **El ESP32-S3 no decide nada.** Recibe comandos, mueve servo y motor, pesa y reporta.

## Advertencia sobre el L298N

El L298N tiene una caída interna de **1,8 a 3 V**. Con alimentación de 5 V el motor recibe apenas 2–3 V, así que gira lento y con poco par.

Para este proyecto eso es aceptable **si el motor es de engranaje reductor**, porque lo que necesitamos es torque a baja velocidad, no velocidad. Si en las pruebas el tornillo se atasca, la solución no es otro driver: es **subir el bloque de potencia a 9–12 V**, que es justo lo que hace J8.

## Regenerar los planos

```bash
kicad-cli sch export svg --output /tmp/plano hardware/kicad/smartpet_bowl.kicad_sch
kicad-cli sch export pdf --output /tmp/plano/smartpet_bowl.pdf hardware/kicad/smartpet_bowl.kicad_sch
```

## Verificación eléctrica

`kicad-cli sch erc` reporta **0 infracciones** en la rev 4, con todas las comprobaciones activas.

Ese resultado no salió gratis: la rev 3 tenía 17 avisos porque la celda de carga llegaba a etiquetas que no existían en ningún otro pin y porque el ESP32 no tenía pines para `GPIO1` y `GPIO2`. Ahora el HX711 se dibuja como módulo de 8 terminales (los 4 del micro y los 4 de la celda) y la placa tiene los 40 pines reales, así que cada net toca al menos dos pines y los que sobran llevan aspa.

Antes de llevar esto a una placa real habría que asignar footprints y añadir los `PWR_FLAG`.
