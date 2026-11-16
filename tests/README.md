# SmartPet Bowl — Tests y Demostración

## Pruebas de Hardware
### Test 1: Sensor PIR
```bash
# Conectar PIR al GPIO 1 del ESP32-S3
# Mover mano delante del sensor
# Verificar que el led de la placa parpadea o el puerto serial envía "detected"
```

### Test 2: Servo de Tapa
```python
# Script de prueba servo
import machine
import time

servo = machine.PWM(machine.PIN(2), freq=50)
for angle in range(0, 180, 10):
    duty = int(angle / 180 * 102)  # 0-180 grados → 25-125 duty cycle
    servo.duty(duty)
    time.sleep(0.1)
servo.deinit()
```

### Test 3: Celda de Carga HX711
```python
# Usando librería HX711
# Colocar peso de referencia de 100g
# Ajustar factor de calibración hasta leer exactamente 100.0g
```

## Pruebas de Integración
### Test 4: Flujo MQTT completo
1. Arrancar broker Mosquitto en Raspberry Pi 4
2. Conectar ESP32-S3
3. Publicar mensaje de prueba desde Pi: `{"pet_id": "luna", "grams": 45}`
4. Verificar que el servo abre la tapa y la celda registra peso

### Test 5: Demostración en vivo
1. Simular mascota con peluche naranja (gato) → sistema debe reconocer y abrir plato
2. Simular mascota con peluche azul (perro) → sistema debe reconocer y abrir plato
3. Simular dos mascotas simultáneamente → sistema debe cerrar tapa y generar alerta

## Criterios de Aceptación
- [ ] Identificación de mascota por color en < 2 segundos
- [ ] Apertura del servo en < 500ms
- [ ] Pesaje con precisión de ± 5g
- [ ] Cierre automático en < 1 segundo
- [ ] Latencia MQTT < 100ms
- [ ] Dashboard Node-RED mostrando video en vivo y consumo