"""Cliente MQTT del comedero.

El ESP32 escucha las ordenes que publica la Raspberry y las ejecuta:

  llamada   -> dosifica los gramos, abre la tapa y toca el nombre
  servir    -> abre la tapa
  cerrar    -> corta el motor y cierra la tapa
  reiniciar -> reinicia la placa

Va en su propio hilo para que el panel siga respondiendo mientras espera.
"""

import _thread
import json
import time

from umqtt.simple import MQTTClient

import network

import config
import hardware

_cliente = None
TEMA = b"comedero/" + config.FEEDER_CODE.encode() + b"/comando/#"


def _al_recibir(tema, mensaje):
    tema = tema.decode()
    try:
        datos = json.loads(mensaje)
    except (ValueError, TypeError):
        datos = {}

    if tema.endswith("/llamada"):
        nombre = datos.get("mascota", "")
        gramos = float(datos.get("gramos", 0) or 0)
        print("Orden: servir", gramos, "g a", nombre)
        hardware.dose(nombre, gramos)
        hardware.servo(config.TAPA_ABIERTA)
        if nombre:
            hardware.llamar(nombre)

    elif tema.endswith("/servir"):
        hardware.servo(config.TAPA_ABIERTA)

    elif tema.endswith("/cerrar"):
        hardware.motor(False)
        hardware.servo(config.TAPA_CERRADA)

    elif tema.endswith("/reiniciar"):
        import machine
        machine.reset()


def publish_event(sufijo, datos):
    """Publica un evento del comedero (sobrante, peso...)."""
    if _cliente is None:
        return False
    tema = b"comedero/" + config.FEEDER_CODE.encode() + b"/evento/" + sufijo.encode()
    _cliente.publish(tema, json.dumps(datos))
    return True


def _bucle(host):
    global _cliente
    while True:
        try:
            if _cliente is None:
                _cliente = MQTTClient(
                    "comedero-" + config.FEEDER_CODE,
                    host,
                    port=config.MQTT_PORT,
                    keepalive=30,
                )
                _cliente.set_callback(_al_recibir)
                _cliente.connect()
                _cliente.subscribe(TEMA)
                try:
                    ip = network.WLAN(network.STA_IF).ifconfig()[0]
                    _cliente.publish(
                        b"comedero/" + config.FEEDER_CODE.encode() + b"/ip",
                        json.dumps({"ip": ip}),
                        retain=True,
                    )
                    print("IP publicada:", ip)
                except Exception as error:  # noqa: BLE001
                    print("no pude publicar la IP:", error)
                hardware.set_mqtt(True)
                print("MQTT conectado a", host)
            _cliente.check_msg()
        except Exception as error:  # noqa: BLE001 - reintenta sin tumbar el panel
            print("MQTT:", error)
            hardware.set_mqtt(False)
            _cliente = None
            time.sleep(3)
        time.sleep_ms(100)


def iniciar(host):
    _thread.start_new_thread(_bucle, (host,))
