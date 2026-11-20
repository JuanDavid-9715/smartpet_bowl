#pragma once

// Placa: Freenove ESP32-S3-WROOM CAM (ESP32-S3-WROOM-1 con PSRAM octal).
// Verificado contra el pinout oficial: los pines de camara coinciden.
//
// IMPORTANTE: GPIO35, GPIO36 y GPIO37 estan ocupados por el PSRAM del modulo.
// No se pueden usar: si se manejan, se corrompe la memoria.

// --- Red -----------------------------------------------------------------
// Las credenciales viven en secrets.h, que no se versiona.
// Copia include/secrets.example.h a include/secrets.h y completalo.
#if !__has_include("secrets.h")
#error "Falta include/secrets.h: copia secrets.example.h y pon tus datos."
#endif
#include "secrets.h"

#define MQTT_PORT 1883
#define FEEDER_CODE "SPB-42"

// --- Actuadores ----------------------------------------------------------
#define PIN_SERVO 14            // SG90, PWM
#define PIN_BUZZER 21           // modulo buzzer activo, I/O
#define PIN_MOTOR_IN1 47        // L298N IN1
#define PIN_MOTOR_IN2 48        // L298N IN2 (comparte pin con el LED WS2812 de la placa)
#define PIN_MOTOR_ENA -1        // -1 = ENA puenteado a 5V (sin control de velocidad)

// --- Sensores ------------------------------------------------------------
#define PIN_HX711_DT 40
#define PIN_HX711_SCK 39

#define PIN_TOF_SCL 1           // VL53L0X SCL  (cableado real)
#define PIN_TOF_SDA 2           // VL53L0X SDA  (cableado real)
#define PIN_TOF_XSHUT 41        // debe ir en ALTO o el sensor queda apagado
#define PIN_TOF_INT 42          // GPIO1 del modulo; se usa solo si se interrumpe

// --- Camara OV2640 (pinout Freenove) -------------------------------------
#define CAM_PIN_PWDN -1
#define CAM_PIN_RESET -1
#define CAM_PIN_XCLK 15
#define CAM_PIN_SIOD 4
#define CAM_PIN_SIOC 5
#define CAM_PIN_VSYNC 6
#define CAM_PIN_HREF 7
#define CAM_PIN_PCLK 13

// D0..D7 en el orden que espera esp_camera
#define CAM_PIN_D0 11   // Y2
#define CAM_PIN_D1 9    // Y3
#define CAM_PIN_D2 8    // Y4
#define CAM_PIN_D3 10   // Y5
#define CAM_PIN_D4 12   // Y6
#define CAM_PIN_D5 18   // Y7
#define CAM_PIN_D6 17   // Y8
#define CAM_PIN_D7 16   // Y9

// --- Mecanica ------------------------------------------------------------
#define TAPA_CERRADA 20
#define TAPA_ABIERTA 105
#define MOTOR_PWM 255           // sin ENA por GPIO, el motor va a tope
#define MOTOR_ARRANQUE_MS 250
#define DOSIS_TIMEOUT_MS 12000
#define PESO_TOLERANCIA_G 3.0
#define SOBRANTE_ESPERA_MS 3000

// --- Tiempos -------------------------------------------------------------
#define PRESENCIA_MM 700
#define PRESENCIA_MS 1500
#define ESTADO_MS 30000
