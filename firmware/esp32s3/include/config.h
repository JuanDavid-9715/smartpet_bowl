#pragma once

// --- Red -----------------------------------------------------------------
#define WIFI_SSID "CAMBIAR"
#define WIFI_PASS "CAMBIAR"

#define MQTT_HOST "192.168.1.10"
#define MQTT_PORT 1883
#define FEEDER_CODE "SPB-42"

// --- Pines ---------------------------------------------------------------
// Ajusta estos numeros al montaje real. Estan elegidos para no chocar con el
// bus de la camara en un ESP32-S3 DevKitC-1.
#define PIN_SERVO_TAPA 13      // servo de la tapa (PWM 50 Hz)
#define PIN_MOTOR_ENA 4        // PWM del L298N (velocidad del dosificador)
#define PIN_MOTOR_IN1 5        // sentido del motor
#define PIN_MOTOR_IN2 6
#define PIN_HX711_DT 7
#define PIN_HX711_SCK 15
#define PIN_BUZZER 16
#define PIN_I2C_SDA 8
#define PIN_I2C_SCL 9

// --- Mecanica ------------------------------------------------------------
#define TAPA_CERRADA 20
#define TAPA_ABIERTA 105
#define MOTOR_PWM 180          // 0-255. Se baja a 120 cerca del objetivo.
#define MOTOR_PWM_FINO 120
#define MOTOR_ARRANQUE_MS 400
#define DOSIS_TIMEOUT_MS 12000
#define PESO_TOLERANCIA_G 3.0
#define SOBRANTE_ESPERA_MS 3000

// --- Camara --------------------------------------------------------------
// Pines del modulo OV2640. Cambian segun la placa; verifica con la tuya.
#define CAM_PIN_PWDN -1
#define CAM_PIN_RESET -1
#define CAM_PIN_XCLK 15
#define CAM_PIN_SIOD 4
#define CAM_PIN_SIOC 5
#define CAM_PIN_D7 16
#define CAM_PIN_D6 17
#define CAM_PIN_D5 18
#define CAM_PIN_D4 12
#define CAM_PIN_D3 10
#define CAM_PIN_D2 8
#define CAM_PIN_D1 9
#define CAM_PIN_D0 11
#define CAM_PIN_VSYNC 6
#define CAM_PIN_HREF 7
#define CAM_PIN_PCLK 13

// --- Tiempos -------------------------------------------------------------
#define PRESENCIA_MM 700       // distancia a la que se considera que hay animal
#define PRESENCIA_MS 1500      // debe sostenerse para no disparar por sombras
#define ESTADO_MS 30000
