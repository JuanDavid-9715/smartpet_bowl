# SmartPet Bowl

Sistema de alimentacion inteligente multimascota con control nutricional diferenciado por vision artificial.

**Empresa:** Quantum Automata  
**Producto:** SmartPet Bowl  
**Materia:** Sistemas Digitales III — ECCI

## Problema
Perros y gatos no pueden compartir dieta. El consumo cruzado de alimento causa cardiomiopatia en gatos y pancreatitis en perros. En hogares multimascota, el animal dominante tambien monopoliza el plato y desnutre al mas timido.

## Solucion
Un plato inteligente que identifica a la mascota por vision, autoriza su racion, abre la tapa, pesa el consumo real en gramos y bloquea el acceso a mascotas no autorizadas.

## Arquitectura
- **ESP32-S3:** control de tiempo real del servo, celda de carga HX711, camara, altavoz y seguridad local.
- **Raspberry Pi 4:** vision artificial, decision, broker MQTT, base de datos y dashboard Node-RED.
- **MQTT:** comunicacion entre el plato y el hub.
- **Node-RED:** monitoreo, historial y control remoto.
- **Cloudflare Tunnel / ngrok:** exposicion publica para la demostracion.

## Estructura del repositorio
```text
smartpet_bowl/
├── design/
│   ├── drawio/
│   ├── penpot/
│   └── exports/
├── hardware/
│   ├── kicad/
│   └── BOM.csv
├── firmware/
│   └── esp32s3/
├── software/
│   ├── raspberry-pi/
│   └── node-red/
├── tests/
├── AGENTS.md
├── README.md
├── LICENSE
├── .gitignore
└── Makefile
```

## Estado
Proyecto en fase de estructura y documentacion. Aun no hay implementacion funcional.

## Licencia
MIT. Copyright (c) 2026 Juan David Medellin Calderon.
