# SmartPet Bowl — Makefile

.PHONY: help setup models firmware upload python node-red test clean

help:
	@echo "Targets:"
	@echo "  setup     Instala dependencias de Python"
	@echo "  models    Descarga el modelo de deteccion (11 MB)"
	@echo "  firmware  Compila firmware ESP32-S3 con PlatformIO"
	@echo "  upload    Flashea el ESP32-S3"
	@echo "  python    Ejecuta el script de Raspberry Pi"
	@echo "  node-red  Inicia Node-RED con el flujo del proyecto"
	@echo "  test      Ejecuta pruebas"
	@echo "  clean     Limpia artifacts"

setup:
	pip install -r software/raspberry-pi/requirements.txt

models:
	@mkdir -p software/web/models software/raspberry-pi/models
	@for d in software/web/models software/raspberry-pi/models; do \
	  [ -f $$d/yolo11n.onnx ] || curl -L -o $$d/yolo11n.onnx \
	    https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.onnx; \
	done
	@ls -la software/web/models/yolo11n.onnx software/raspberry-pi/models/yolo11n.onnx

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
