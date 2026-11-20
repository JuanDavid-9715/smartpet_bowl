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
    "frame_size": FrameSize.SVGA,    # 800x600: el enlace WiFi manda
    "jpeg_quality": 80,              # es un porcentaje: mas alto = mejor
    "fb_count": 2,
}

# Techo de ganancia para poca luz y brillo extra (-2..2). Medido: sin esto la
# imagen nocturna queda en luminancia 16/255; con 16X sube a 85.
CAMERA_GAIN = "16X"
CAMERA_BRIGHTNESS = 1

# --- Servidor de video ----------------------------------------------------
HTTP_PORT = 80
# vga (fluido), svga (equilibrado) o hd (nitido). Se puede cambiar desde la web.
DEFAULT_SIZE = "svga"

# --- Actuadores y sensores (etapas siguientes) ----------------------------
PIN_SERVO = 14
PIN_BUZZER = 21
PIN_MOTOR_IN1 = 47
PIN_MOTOR_IN2 = 48
PIN_HX711_DT = 40
PIN_HX711_SCK = 39
PIN_TOF_SCL = 1
PIN_TOF_SDA = 2
PIN_TOF_XSHUT = 41
PIN_TOF_INT = 42

# --- MQTT ----------------------------------------------------------------
MQTT_PORT = 1883
MQTT_KEEPALIVE = 30
