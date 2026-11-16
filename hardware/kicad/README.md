# KiCad — Planos electricos

Este proyecto usa KiCad unicamente para el esquematico electrico y el diagrama de conexiones.
No se fabrica PCB ni se modelan piezas 3D.

## Archivos previstos
- `smartpet_bowl.kicad_pro` — proyecto KiCad
- `smartpet_bowl.kicad_sch` — esquematico
- `libraries/` — simbolos y footprints propios
- `exports/` — PDF/SVG de los planos

## Alcance
- Conexion Raspberry Pi 4 ↔ ESP32-S3
- Alimentacion del servo y la celda de carga
- Pines del sensor PIR, HX711, servo, altavoz y camara
