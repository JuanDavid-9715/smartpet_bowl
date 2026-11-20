// SmartPet Bowl — firmware del comedero.
//
// El ESP32-S3 no decide quien come: recibe comandos, mueve servo y motor,
// pesa y reporta. La identificacion ocurre en la Raspberry Pi.
//
// Secuencia acordada:
//   1. A la hora de comer, el servicio pide "llamada {gramos, segundos}".
//   2. El dosificador sirve la racion con la tapa CERRADA.
//   3. Suena el buzzer y se abre la tapa para que la mascota se acerque.
//   4. El sensor de distancia detecta presencia y se publica el evento.
//   5. La Raspberry identifica; si es la mascota correcta llega "servir",
//      si no llega "cerrar".
//   6. Al cerrar la ventana se mide el sobrante y se reporta.

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <ESP32Servo.h>
#include <HX711.h>
#include <Wire.h>
#include <Adafruit_VL53L0X.h>
#include <ESPmDNS.h>
#include "esp_camera.h"
#include "esp_http_server.h"
#include "config.h"

enum State {
  ST_BOOT,
  ST_CONNECTING,
  ST_IDLE,
  ST_CALLING,
  ST_SERVING,
  ST_WEIGHING,
  ST_ERROR
};

static State state = ST_BOOT;
static Servo tapa;
static HX711 scale;
static Adafruit_VL53L0X tof;
static WiFiClient net;
static PubSubClient mqtt(net);
static httpd_handle_t cameraServer = nullptr;

static float pesoBase = 0;
static float pesoServido = 0;
static unsigned long llamadaHasta = 0;
static unsigned long presenciaDesde = 0;
static unsigned long ultimoEstado = 0;
static bool tapaAbierta = false;
static String mascotaActual = "";

// ---------------------------------------------------------------- utilidades

static void publicar(const char *sufijo, JsonDocument &doc) {
  char buffer[256];
  size_t largo = serializeJson(doc, buffer, sizeof(buffer));
  String tema = String("comedero/") + FEEDER_CODE + "/" + sufijo;
  mqtt.publish(tema.c_str(), (const uint8_t *)buffer, largo, false);
  Serial.printf("-> %s %s\n", tema.c_str(), buffer);
}

static void eventoSimple(const char *sufijo, const char *clave, float valor) {
  JsonDocument doc;
  doc[clave] = valor;
  publicar(sufijo, doc);
}

static void abrirTapa() {
  tapa.write(TAPA_ABIERTA);
  tapaAbierta = true;
}

static void cerrarTapa() {
  tapa.write(TAPA_CERRADA);
  tapaAbierta = false;
}

static void sonar(int veces) {
  for (int i = 0; i < veces; i++) {
    digitalWrite(PIN_BUZZER, HIGH);
    delay(180);
    digitalWrite(PIN_BUZZER, LOW);
    delay(140);
  }
}

static float leerPeso(int muestras = 8) {
  if (!scale.is_ready()) return -1;
  return scale.get_units(muestras);
}

// ---------------------------------------------------------------- dosificador

// Sirve gramos con lazo cerrado sobre la celda de carga.
// Baja la velocidad cerca del objetivo para no pasarse por inercia.
static float dosificar(float gramos) {
  if (gramos <= 0) return 0;

  unsigned long inicio = millis();
  float referencia = leerPeso(10);
  if (referencia < 0) referencia = pesoBase;
  float objetivo = referencia + gramos;

  digitalWrite(PIN_MOTOR_IN1, HIGH);
  digitalWrite(PIN_MOTOR_IN2, LOW);
#if PIN_MOTOR_ENA >= 0
  analogWrite(PIN_MOTOR_ENA, MOTOR_PWM);
#endif
  delay(MOTOR_ARRANQUE_MS);

  float actual = referencia;
  while (millis() - inicio < DOSIS_TIMEOUT_MS) {
    actual = leerPeso(4);
    if (actual < 0) {
      // La celda no responde: esperar sin girar a maxima velocidad en vacio.
      delay(60);
      continue;
    }
    float falta = objetivo - actual;
    if (falta <= PESO_TOLERANCIA_G) break;
    delay(60);
  }

#if PIN_MOTOR_ENA >= 0
  analogWrite(PIN_MOTOR_ENA, 0);
#endif
  digitalWrite(PIN_MOTOR_IN1, LOW);
  delay(250);

  float final_ = leerPeso(10);
  if (final_ < 0) final_ = actual;
  return max(0.0f, final_ - referencia);
}

// ---------------------------------------------------------------- camara

static esp_err_t streamHandler(httpd_req_t *req) {
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    httpd_resp_send_500(req);
    return ESP_FAIL;
  }
  httpd_resp_set_type(req, "image/jpeg");
  httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=capture.jpg");
  esp_err_t res = httpd_resp_send(req, (const char *)fb->buf, fb->len);
  esp_camera_fb_return(fb);
  return res;
}

static bool iniciarCamara() {
  camera_config_t cfg = {};
  cfg.ledc_channel = LEDC_CHANNEL_0;
  cfg.ledc_timer = LEDC_TIMER_0;
  cfg.pin_d0 = CAM_PIN_D0;
  cfg.pin_d1 = CAM_PIN_D1;
  cfg.pin_d2 = CAM_PIN_D2;
  cfg.pin_d3 = CAM_PIN_D3;
  cfg.pin_d4 = CAM_PIN_D4;
  cfg.pin_d5 = CAM_PIN_D5;
  cfg.pin_d6 = CAM_PIN_D6;
  cfg.pin_d7 = CAM_PIN_D7;
  cfg.pin_xclk = CAM_PIN_XCLK;
  cfg.pin_pclk = CAM_PIN_PCLK;
  cfg.pin_vsync = CAM_PIN_VSYNC;
  cfg.pin_href = CAM_PIN_HREF;
  cfg.pin_sccb_sda = CAM_PIN_SIOD;
  cfg.pin_sccb_scl = CAM_PIN_SIOC;
  cfg.pin_pwdn = CAM_PIN_PWDN;
  cfg.pin_reset = CAM_PIN_RESET;
  cfg.xclk_freq_hz = 20000000;
  cfg.pixel_format = PIXFORMAT_JPEG;
  cfg.frame_size = FRAMESIZE_VGA;
  cfg.jpeg_quality = 12;
  cfg.fb_count = 2;
  cfg.grab_mode = CAMERA_GRAB_LATEST;
  return esp_camera_init(&cfg) == ESP_OK;
}

static void iniciarServidorCamara() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 81;
  config.ctrl_port = 32768;

  httpd_uri_t capture = {.uri = "/capture", .method = HTTP_GET, .handler = streamHandler, .user_ctx = nullptr};
  httpd_uri_t stream = {.uri = "/stream", .method = HTTP_GET, .handler = streamHandler, .user_ctx = nullptr};

  if (httpd_start(&cameraServer, &config) == ESP_OK) {
    httpd_register_uri_handler(cameraServer, &capture);
    httpd_register_uri_handler(cameraServer, &stream);
    Serial.println("Camara disponible en :81/capture");
  }
}

// ---------------------------------------------------------------- comandos

static void manejarComando(char *tema, byte *carga, unsigned int largo) {
  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, carga, largo);
  if (err) {
    Serial.printf("JSON invalido: %s\n", err.c_str());
    return;
  }
  String sufijo = String(tema);
  sufijo = sufijo.substring(sufijo.lastIndexOf('/') + 1);

  if (sufijo == "llamada") {
    // Servir primero, con la tapa cerrada, y despues llamar.
    float gramos = doc["gramos"] | 0.0f;
    int segundos = doc["segundos"] | 20;
    mascotaActual = String((const char *)(doc["mascota"] | ""));

    float servido = dosificar(gramos);
    pesoServido = servido;
    eventoSimple("evento/peso", "gramos", servido);

    sonar(2);
    abrirTapa();
    llamadaHasta = millis() + (unsigned long)segundos * 1000UL;
    state = ST_CALLING;
    Serial.printf("Llamada: %s, %.1f g servidos\n", mascotaActual.c_str(), servido);

  } else if (sufijo == "servir") {
    mascotaActual = String((const char *)(doc["mascota"] | ""));
    abrirTapa();
    llamadaHasta = millis() + 900000UL;  // ventana de comida: 15 min
    state = ST_CALLING;

  } else if (sufijo == "cerrar") {
    cerrarTapa();
    state = ST_WEIGHING;

  } else if (sufijo == "reiniciar") {
    Serial.println("Reinicio solicitado");
    delay(200);
    ESP.restart();
  }
}

// La IP de la Raspberry cambia con el punto de acceso del celular, asi que se
// busca por nombre mDNS. La IP fija solo se usa si el nombre no responde.
static void iniciarMdns() {
  static bool listo = false;
  if (listo) return;
  if (MDNS.begin("smartpet-bowl")) {
    listo = true;
    Serial.println("mDNS activo: smartpet-bowl.local");
  }
}

static IPAddress direccionBroker() {
  static IPAddress cache;
  if ((uint32_t)cache != 0) return cache;

  IPAddress porNombre = MDNS.queryHost(MQTT_HOST_NAME, 3000);
  if ((uint32_t)porNombre != 0) {
    cache = porNombre;
    Serial.printf("Broker por mDNS: %s = %s\n", MQTT_HOST_NAME, cache.toString().c_str());
    return cache;
  }

  IPAddress fija;
  if (fija.fromString(MQTT_HOST_FALLBACK)) {
    Serial.printf("mDNS sin respuesta, uso la IP de respaldo %s\n", MQTT_HOST_FALLBACK);
    return fija;
  }
  return IPAddress(0, 0, 0, 0);
}

static void conectarMqtt() {
  iniciarMdns();
  IPAddress broker = direccionBroker();
  if ((uint32_t)broker == 0) {
    Serial.println("Sin direccion para el broker MQTT");
    return;
  }
  mqtt.setServer(broker, MQTT_PORT);
  String clientId = String("comedero-") + FEEDER_CODE;
  String willTopic = String("comedero/") + FEEDER_CODE + "/estado";

  if (mqtt.connect(clientId.c_str(), nullptr, nullptr,
                   willTopic.c_str(), 1, true, "{\"en_linea\":false}")) {
    String base = String("comedero/") + FEEDER_CODE + "/comando/#";
    mqtt.subscribe(base.c_str(), 1);
    mqtt.publish(willTopic.c_str(), "{\"en_linea\":true}", true);
    state = ST_IDLE;
    Serial.println("MQTT conectado");
  }
}

// ---------------------------------------------------------------- ciclo

void setup() {
  Serial.begin(115200);
  delay(200);
  pinMode(PIN_MOTOR_IN1, OUTPUT);
  pinMode(PIN_MOTOR_IN2, OUTPUT);
#if PIN_MOTOR_ENA >= 0
  pinMode(PIN_MOTOR_ENA, OUTPUT);
  analogWrite(PIN_MOTOR_ENA, 0);
#endif
  pinMode(PIN_BUZZER, OUTPUT);

  tapa.attach(PIN_SERVO, 500, 2400);
  cerrarTapa();

  scale.begin(PIN_HX711_DT, PIN_HX711_SCK);
  scale.set_scale(-430.0);  // ajustar con un peso conocido en el montaje
  delay(400);
  scale.tare(20);
  pesoBase = leerPeso(12);

  // XSHUT del VL53L0X debe estar en alto: si no, el sensor queda apagado.
  pinMode(PIN_TOF_XSHUT, OUTPUT);
  digitalWrite(PIN_TOF_XSHUT, HIGH);
  delay(20);

  Wire.begin(PIN_TOF_SDA, PIN_TOF_SCL);
  Wire.setClock(100000);
  if (!tof.begin()) {
    Serial.printf("VL53L0X no responde (SDA=%d SCL=%d)\n", PIN_TOF_SDA, PIN_TOF_SCL);
  }

  if (!iniciarCamara()) {
    Serial.println("Camara no inicializada");
  } else {
    iniciarServidorCamara();
  }

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  state = ST_CONNECTING;

  mqtt.setCallback(manejarComando);
  mqtt.setBufferSize(512);
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    state = ST_CONNECTING;
    delay(500);
    return;
  }
  if (!mqtt.connected()) {
    conectarMqtt();
    delay(1000);
    return;
  }
  mqtt.loop();

  // Presencia por distancia, con debounce para no disparar con sombras.
  VL53L0X_RangingMeasurementData_t m;
  tof.rangingTest(&m, false);
  bool cerca = (m.RangeStatus != 4) && (m.RangeMilliMeter > 30) && (m.RangeMilliMeter < PRESENCIA_MM);
  if (cerca && presenciaDesde == 0) {
    presenciaDesde = millis();
  } else if (!cerca) {
    presenciaDesde = 0;
  }
  if (presenciaDesde && millis() - presenciaDesde > PRESENCIA_MS) {
    presenciaDesde = 0;
    JsonDocument doc;
    doc["distancia_mm"] = m.RangeMilliMeter;
    publicar("evento/presencia", doc);
    if (state == ST_IDLE) state = ST_SERVING;
  }

  // Fin de la ventana de llamada: cerrar y medir sobrante.
  if (llamadaHasta && millis() > llamadaHasta) {
    llamadaHasta = 0;
    cerrarTapa();
    delay(SOBRANTE_ESPERA_MS);
    float sobrante = max(0.0f, leerPeso(12) - pesoBase);
    JsonDocument doc;
    doc["gramos"] = sobrante;
    doc["mascota"] = mascotaActual.c_str();
    doc["duracion_s"] = 0;
    publicar("evento/sobrante", doc);
    pesoServido = 0;
    mascotaActual = "";
    state = ST_IDLE;
  }

  if (millis() - ultimoEstado > ESTADO_MS) {
    ultimoEstado = millis();
    JsonDocument doc;
    doc["en_linea"] = true;
    doc["version"] = "1.0.0";
    doc["estado"] = (int)state;
    publicar("estado", doc);
  }

  delay(50);
}
