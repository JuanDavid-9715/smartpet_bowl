# KiCad — Esquemático eléctrico

Este proyecto usa KiCad únicamente para el esquemático eléctrico. **No se fabrica PCB ni se modelan piezas 3D.**

## Archivos

- `smartpet_bowl.kicad_sch` — esquemático del comedero, hoja única A3, rev 3.
- `exports/smartpet_bowl.pdf` — plano para imprimir o anexar al documento.
- `exports/smartpet_bowl.svg` — plano vectorial para presentaciones.

## Qué representa

El comedero se arma con **módulos comprados** unidos por conectores, no con componentes soldados. Por eso el plano es de conectores y nets.

| Ref | Módulo | Nets |
|---|---|---|
| J1 | Entrada 5 V / 3 A | `+5V_IN`, `GND` |
| J2 | Regulador 3V3 | `+5V_IN`, `+3V3`, `GND` |
| J3 | ESP32-S3 DevKit (2×15) | ver tabla de pines |
| J4 | Cámara OV2640 | `+3V3`, `GND`, `CAM_SIOD`, `CAM_SIOC`, `CAM_PCLK`, `CAM_VSYNC` |
| J5 | VL53L0X o VL6180X | `+3V3`, `GND`, `TOF_SDA`, `TOF_SCL` |
| J6 | Módulo HX711 | `+3V3`, `HX711_DT`, `HX711_SCK`, `GND` |
| J7 | Celda de carga | `LC_E+`, `LC_E-`, `LC_A+`, `LC_A-` |
| J8 | L298N, bloque de control | `MOTOR_IN1`, `MOTOR_IN2`, `MOTOR_ENA`, `+5V_IN`, `GND` |
| J11 | L298N, bloque de potencia | `+5V_IN`, `GND`, `MOTOR_OUT1`, `MOTOR_OUT2` |
| J9 | Motor del dosificador | `MOTOR_OUT1`, `MOTOR_OUT2` |
| J10 | Servo de la tapa MG996R | `SERVO_TAPA`, `+5V`, `GND` |
| BZ1 | Buzzer activo 3.3 V | `BUZZ`, `GND` |

### Pines del ESP32-S3 usados

`+3V3`, `GND`, `CAM_SIOD`, `CAM_SIOC`, `CAM_PCLK`, `CAM_VSYNC`, `TOF_SDA`, `TOF_SCL`, `HX711_DT`, `HX711_SCK`, `SERVO_TAPA`, `MOTOR_ENA`, `MOTOR_IN1`, `MOTOR_IN2`, `BUZZ`, `+5V`.

El resto queda libre a propósito. UART se omitió porque en este alcance no hay consola externa.

## Decisiones de diseño

- **Tapa y dosificador son mecanismos distintos.** El servo MG996R abre la tapa; el motor DC mueve un tornillo sin fin que dosifica. Una sola compuerta no puede hacer las dos cosas: si queda abierta, la comida cae libre y se pierde el control de porción.
- **Tornillo sin fin en lugar de compuerta estranguladora.** El tornillo mueve un volumen casi constante por vuelta y no depende de la gravedad ni del nivel del depósito. Una compuerta por gravedad atasca croquetas irregulares y su caudal cambia con la humedad.
- **El lazo lo cierra la celda de carga, no el motor.** El motor gira y la celda decide cuándo parar, así que la precisión viene de la báscula.
- **El servo va a 5 V directo.** Un MG996R pide más de 1 A en el arranque; alimentarlo del regulador del ESP32 provoca reinicios.
- **Sensor de distancia en vez de infrarrojo pasivo.** El VL53L0X/6180X dice *a qué distancia* está el animal, no solo que hay movimiento. Eso permite descartar sombras y objetos.
- **Buzzer activo de 3.3 V al GPIO, sin resistencia ni amplificador.** Consume pocos miliamperios y no necesita etapa de potencia. Se descartó el MAX98357A por no sumar componentes.
- **El ESP32-S3 no decide nada.** Recibe comandos, mueve servo y motor, pesa y reporta.

## Advertencia sobre el L298N

El L298N tiene una caída interna de **1,8 a 3 V**. Con una alimentación de 5 V, el motor recibe apenas 2–3 V, así que gira lento y con poco par.

Para este proyecto eso es aceptable **si el motor es de engranaje reductor** (por ejemplo 1:100), porque lo que necesitamos es torque a baja velocidad, no velocidad. Si en las pruebas el tornillo se atasca, la solución no es otro driver: es **subir la alimentación del bloque de potencia a 9–12 V** y dejar el regulador solo para la lógica.

## Regenerar los planos

```bash
kicad-cli sch export svg --output hardware/kicad/exports hardware/kicad/smartpet_bowl.kicad_sch
kicad-cli sch export pdf --output hardware/kicad/exports/smartpet_bowl.pdf hardware/kicad/smartpet_bowl.kicad_sch
```

## Verificación eléctrica

`kicad-cli sch erc` reporta **17 avisos**, todos esperados en un plano de módulos:

- **13 `pin_not_connected`** — pines del ESP32-S3 que no se usan, a propósito.
- **4 `isolated_pin_label`** — `LC_E+`, `LC_E-`, `LC_A+`, `LC_A-` aparecen una sola vez porque la celda se conecta a los bornes del propio módulo HX711, que no se modelan como pines.

**No hay cortos, ni nets con dos conductores, ni puntos fuera de rejilla.** Ese último grupo sí existía en la revisión 2: había 65 endpoints fuera de la grilla de 1,27 mm. Se corrigió ajustando cada módulo a múltiplos de 1,27.

Antes de llevar esto a una placa real habría que asignar footprints y añadir los `PWR_FLAG`.
