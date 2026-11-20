"""Conexion WiFi con reintentos."""

import network
import time


def connect(ssid, password, timeout=30):
    """Conecta en modo estacion y devuelve el objeto WLAN ya conectado."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        return wlan

    wlan.connect(ssid, password)
    start = time.ticks_ms()

    while not wlan.isconnected():
        if time.ticks_diff(time.ticks_ms(), start) > timeout * 1000:
            raise OSError("WiFi: no conecta con %s" % ssid)
        time.sleep_ms(300)

    return wlan


def ip(wlan):
    return wlan.ifconfig()[0]


def rssi(wlan):
    try:
        return wlan.status("rssi")
    except (OSError, ValueError):
        return None
