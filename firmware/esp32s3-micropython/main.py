"""Arranque del comedero: WiFi + visor de la camara.

Se ejecuta solo al encender la placa. Ctrl-C en el REPL lo detiene.
"""

import sys

import cam
import config
import hardware
import secrets
import stream
import wifi


def main():
    print("SmartPet Bowl ·", config.FEEDER_CODE)
    print("Conectando a WiFi '%s'…" % secrets.WIFI_SSID)

    wlan = wifi.connect(secrets.WIFI_SSID, secrets.WIFI_PASS)
    ip = wifi.ip(wlan)
    print("WiFi OK · IP", ip)
    print("RSSI", wifi.rssi(wlan), "dBm")

    camara = cam.camera()
    print("Camara:", cam.info(camara))

    hardware.init()
    print("Hardware listo: servo", config.TAPA_CERRADA, "grados")
    print("Abre en el navegador: http://%s/" % ip)

    stream.serve(ip)


try:
    main()
except KeyboardInterrupt:
    print("detenido desde el REPL")
except Exception as error:  # noqa: BLE001 - el REPL debe seguir vivo
    sys.print_exception(error)
