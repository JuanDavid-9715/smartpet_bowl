#pragma once

// Plantilla de credenciales. Copia este archivo como secrets.h y completa.
//
//   cp include/secrets.example.h include/secrets.h
//
// secrets.h esta en .gitignore: tus claves no viajan al repositorio.

// WiFi al que se conecta el comedero.
#define WIFI_SSID "NOMBRE_DE_LA_RED"
#define WIFI_PASS "CLAVE_DEL_WIFI"

// Nombre mDNS de la Raspberry. Se resuelve en cada arranque, asi que sirve
// aunque el router le asigne otra IP.
#define MQTT_HOST_NAME "raspberrypi.local"

// IP fija de respaldo, por si el punto de acceso bloquea el multicast mDNS.
#define MQTT_HOST_FALLBACK "192.168.1.50"
