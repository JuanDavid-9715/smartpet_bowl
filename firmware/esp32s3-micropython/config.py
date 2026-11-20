"""Ajustes del comedero SmartPet Bowl (MicroPython).

Pines verificados contra el cableado real del montaje (netlist de KiCad rev 8).
"""

from camera import PixelFormat, FrameSize

# --- Identidad ------------------------------------------------------------
FEEDER_CODE = "SPB-42"

# --- Camara OV2640 (Freenove ESP32-S3-WROOM CAM) --------------------------
# data_pins en el orden D0..D7, que en la placa es Y2, Y3, Y4, Y5, Y6, Y7, Y8, Y9.
CAMERA = {
    "data_pins": [11, 9, 8, 10, 12, 18, 17, 16],
    "vsync_pin": 6,
    "href_pin": 7,
    "pclk_pin": 13,
    "xclk_pin": 15,
    "sda_pin": 4,
    "scl_pin": 5,
    "powerdown_pin": -1,
    "reset_pin": -1,
    "pixel_format": PixelFormat.JPEG,
    "frame_size": FrameSize.VGA,     # 640x480: el enlace WiFi manda
    "jpeg_quality": 70,              # es un porcentaje: mas alto = mejor
    "fb_count": 2,
}

# Techo de ganancia para poca luz y brillo extra (-2..2). Medido: sin esto la
# imagen nocturna queda en luminancia 16/255; con 16X sube a 85.
CAMERA_GAIN = "16X"
CAMERA_BRIGHTNESS = 1

# --- Servidor de video ----------------------------------------------------
HTTP_PORT = 80
# vga (fluido), svga (equilibrado) o hd (nitido). Se puede cambiar desde la web.
DEFAULT_SIZE = "vga"

# --- Actuadores y sensores (etapas siguientes) ----------------------------
PIN_SERVO = 14
TAPA_CERRADA = 0         # angulo del servo con la tapa puesta
TAPA_ABIERTA = 50        # angulo con la tapa levantada
MOTOR_DUTY = 6           # porcentaje inicial; 4 % no vence el par, 5-6 % gira lento
DOSIS_TIMEOUT_MS = 30000 # corte de seguridad si la celda nunca llega al objetivo

# --- Ciclo de comida (para la simulacion, corto) --------------------------
GRACE_MS = 8000          # cuanto puede faltar la mascota sin cerrar la tapa
MEAL_MAX_MS = 60000      # tope de una comida completa
PIN_BUZZER = 21
PIN_MOTOR_IN1 = 47
PIN_MOTOR_IN2 = 48
PIN_HX711_DT = 40
PIN_HX711_SCK = 39
PIN_TOF_SCL = 1
PIN_TOF_SDA = 2
PIN_TOF_XSHUT = 41
PRESENCIA_MM = 700       # a menos de esto se considera que hay algo delante
PIN_TOF_INT = 42

# --- MQTT ----------------------------------------------------------------
MQTT_PORT = 1883

# --- Celda de carga -------------------------------------------------------
HX711_SCALE = -430.0     # unidades por gramo; se ajusta con "Calibrar"
MQTT_KEEPALIVE = 30
