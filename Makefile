# SmartPet Bowl — Makefile

.PHONY: help setup firmware upload python node-red test clean

help:
	@echo "Targets:"
	@echo "  setup     Instala dependencias de Python"
	@echo "  firmware  Compila firmware ESP32-S3 con PlatformIO"
	@echo "  upload    Flashea el ESP32-S3"
	@echo "  python    Ejecuta el script de Raspberry Pi"
	@echo "  node-red  Inicia Node-RED con el flujo del proyecto"
	@echo "  test      Ejecuta pruebas"
	@echo "  clean     Limpia artifacts"

setup:
	pip install -r software/raspberry-pi/requirements.txt

firmware:
	cd firmware/esp32s3 && pio run

upload:
	cd firmware/esp32s3 && pio run -t upload

python:
	python3 software/raspberry-pi/main.py

node-red:
	node-red -s software/node-red/flows.json

test:
	python3 -m pytest tests

clean:
	rm -rf build/ dist/ __pycache__/ *.pyc *.db
