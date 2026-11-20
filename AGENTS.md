# AGENTS.md — SmartPet Bowl (Quantum Automata)

## Identidad del proyecto
- **Empresa:** Quantum Automata
- **Producto:** SmartPet Bowl
- **Descripcion:** Sistema de alimentacion inteligente multimascota con control nutricional diferenciado por vision artificial.
- **Materia:** Sistemas Digitales III — ECCI
- **Repositorio:** `smartpet_bowl`

## Objetivo academico
Cumplir los requisitos del proyecto final: Raspberry Pi 4 con camara, ESP32-S3, MQTT, Node-RED, exposicion publica con Cloudflare Tunnel o ngrok y demostracion en vivo.

## Organizacion del repositorio
```text
smartpet_bowl/
├── design/
│   ├── drawio/              # Diagramas .drawio
│   ├── penpot/              # Enlaces y exports de Penpot
│   └── exports/             # PNG/SVG finales
├── hardware/
│   ├── kicad/               # Esquematico electrico (sin PCB)
│   │   ├── libraries/
│   │   └── exports/
│   └── BOM.csv              # Lista de materiales
├── firmware/
│   └── esp32s3/
│       ├── src/
│       ├── include/
│       ├── platformio.ini
│       └── README.md
├── software/
│   ├── raspberry-pi/
│   │   ├── src/
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── README.md
│   └── node-red/
│       ├── flows.json
│       └── README.md
├── tests/
├── AGENTS.md
├── MEMORY.md
├── README.md
├── LICENSE
├── .gitignore
└── Makefile
```

## Reglas de Git
- El repositorio se inicializa dentro de `smartpet_bowl/`.
- Ramas:
  - `main`: estable, protegida.
  - `develop`: integracion del equipo.
  - `feature/<nombre>`: trabajo por funcionalidad.
- Commits convencionales: `feat:`, `fix:`, `docs:`, `test:`, `chore:`, `refactor:`.
- Un commit por unidad de trabajo revisable.
- No incluir credenciales, tokens, claves ni bases de datos.
- No subir `docs/`, `MEMORY.md` ni `scripts/`. Son locales.
- No subir PDFs del profesor ni material con copyright.
- Revisar `git status` y `git diff` antes de cada commit.

## Roles del equipo
- **Stiven** — Economista / Modelo de negocio.
  - BOM, precios en COP, suscripcion, TAM, pitch economico.
- **Juan David** — Tecnico / Arquitectura.
  - Raspberry Pi 4, Python POO, ESP32-S3, MQTT, Node-RED, integracion.
- **Kevin** — Etiologo / UX Cliente.
  - Comportamiento animal, bienestar, experiencia de usuario, justificacion veterinaria.

## Convenciones tecnicas
- Python 3 con POO en Raspberry Pi 4.
- Firmware del ESP32-S3 en **MicroPython** (Python).
- Comunicacion por MQTT.
- Dashboard en Node-RED.
- Precios y presupuesto en COP.
- Documentacion tecnica en espanol neutral.
- Identificadores, nombres de archivos y codigo en ingles.

## Reglas de trabajo
- Todos deben conocer el proyecto completo, no solo su rol.
- No agregar requisitos que el profesor no pidio.
- No prometer reconocimiento facial perfecto: la demo usa deteccion por color/silueta.
- No salir del alcance de 2 semanas.
- Cualquier decision de negocio o arquitectura se registra en `MEMORY.md`.
- No se desarrolla diseno ni programacion sin aprobacion explicita.
- KiCad se usa solo para esquematico electrico. No hay PCB ni modelos 3D.

## Estado actual
- [x] Estructura de carpetas definida.
- [x] Roles asignados.
- [x] Decisiones iniciales registradas.
- [x] Licencia MIT definida.
- [ ] Diagrama de bloques en draw.io.
- [ ] Diseno de interfaz en Penpot.
- [ ] Esquematico en KiCad.
- [ ] Firmware ESP32-S3.
- [ ] Script Python POO.
- [ ] Dashboard Node-RED.
- [ ] Pruebas y demo.
