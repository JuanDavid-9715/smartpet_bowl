"""Cliente MQTT. Publica y escucha al comedero."""
from __future__ import annotations

import json
import logging
from typing import Callable

import paho.mqtt.client as mqtt

from . import config

log = logging.getLogger(__name__)


class MqttClient:
    def __init__(self, handler: Callable[[str, dict], None]):
        self.handler = handler
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.will_set(config.TOPIC_STATE, json.dumps({"en_linea": False}), retain=True)

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        log.info("MQTT conectado (%s)", reason_code)
        client.subscribe(f"{config.TOPIC_EVENT}/#")
        client.subscribe(f"comedero/{config.FEEDER_CODE}/ip")
        client.publish(config.TOPIC_STATE, json.dumps({"en_linea": True}), retain=True)

    def _on_message(self, client, userdata, message):
        try:
            body = json.loads(message.payload.decode("utf-8") or "{}")
        except ValueError:
            body = {}
        self.handler(message.topic, body)

    def connect(self) -> None:
        self.client.connect(config.MQTT_HOST, config.MQTT_PORT, keepalive=45)
        self.client.loop_start()

    def publish(self, suffix: str, body: dict) -> None:
        topic = f"{config.TOPIC_COMMAND}/{suffix}"
        self.client.publish(topic, json.dumps(body), qos=1)
        log.info("-> %s %s", topic, body)

    def stop(self) -> None:
        self.client.publish(config.TOPIC_STATE, json.dumps({"en_linea": False}), retain=True)
        self.client.loop_stop()
        self.client.disconnect()
