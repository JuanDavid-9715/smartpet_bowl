"""Arranque del comedero: WiFi + visor de la camara.

Se ejecuta solo al encender la placa. Ctrl-C en el REPL lo detiene.
"""

import sys
import time

import cam
import config
import hardware
import mqtt
import secrets
import stream
import wifi


def main():
    print("SmartPet Bowl ·", config.FEEDER_CODE)
    print("Conectando a WiFi '%s'…" % secrets.WIFI_SSID)

    # El punto de acceso del celular tarda en aceptar la conexion. Si se rinde
    # al primer intento, la placa se queda sin panel y hay que reiniciarla a
    # mano: por eso reintenta para siempre.
    while True:
        try:
            wlan = wifi.connect(secrets.WIFI_SSID, secrets.WIFI_PASS)
            break
        except OSError as error:
            print("WiFi:", error, "· reintento en 5 s")
            time.sleep(5)

    ip = wifi.ip(wlan)
    print("WiFi OK · IP", ip)
    print("RSSI", wifi.rssi(wlan), "dBm")

    try:
        camara = cam.camera()
        print("Camara:", cam.info(camara))
    except Exception as error:  # noqa: BLE001 - sin camara el panel sigue
        print("Camara no disponible:", error)

    hardware.init()
    print("Hardware listo: servo", config.TAPA_CERRADA, "grados")

    hardware.set_publisher(mqtt.publish_event)
    mqtt.iniciar(secrets.MQTT_HOST_FALLBACK)
    print("Abre en el navegador: http://%s/" % ip)

    stream.serve(ip)


while True:
    try:
        main()
        break
    except KeyboardInterrupt:
        # Ctrl-C desde el REPL: se queda detenido a proposito.
        print("detenido desde el REPL")
        break
    except Exception as error:  # noqa: BLE001 - que se recupere solo
        # Un fallo no debe dejar el comedero muerto hasta que alguien lo
        # desenchufe: se reinicia el programa cada 5 segundos.
        print("Fallo:", error)
        print("reinicio en 5 s")
        time.sleep(5)
