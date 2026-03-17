# mqtt_client.py
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Callable, Dict, Optional

import paho.mqtt.client as mqtt

# Handler-Signatur: (topic, payload str) -> None
MessageHandler = Callable[[str, str], None]

@dataclass(frozen=True)
class MqttSettings:
    host: str
    port: int = 1883
    keepalive: int = 60
    client_id: str = "temp-logger-backend"


class MqttClient:
    def __init__(self, settings: MqttSettings) -> None:
        self.settings = settings
        self._handlers: Dict[str, MessageHandler] = {} # exact-topic routing

        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=settings.client_id
        )
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message

        self._connected = False

    def connect_and_start(self) -> None:
        """
        Connect + loop_start (Thread).
        """
        self._client.connect(
            self.settings.host,
            self.settings.port,
            self.settings.keepalive
        )
        self._client.loop_start()

    def stop_and_disconnect(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()
        self._connected = False

    def subscribe(self, topic: str, handler: MessageHandler, qos: int = 0) -> None:
        """
        Registriert einen Handler und subscribed (wenn bereits connected: direkt).
        paho akzeptiert Wildcards wie + und #
        """
        self._handlers[topic] = handler
        if self._connected:
            self._client.subscribe(topic, qos=qos)

    def publish(self, topic: str, payload: str, qos: int = 0, retain: bool = False) -> None:
        self._client.publish(topic, payload=payload, qos=qos, retain=retain)

    # Optionaler Helper: JSON publish
    def publish_json(self, topic: str, obj: dict, qos: int = 0, retain: bool = False) -> None:
        self.publish(topic, json.dumps(obj), qos=qos, retain=retain)

    def _on_connect(self, client, userdata, flags, rc, properties=None) -> None:
        if rc == 0:
            self._connected = True
            logging.info(f"MQTT connected successfully to {self.settings.host}:{self.settings.port}")
            # Alle registrierten Subscriptions jetzt aktivieren
            for topic in self._handlers.keys():
                client.subscribe(topic, qos=0)
                logging.info(f"Subscribed to topic: {topic}")
        else:
            # rc != 0: Verbindung fehlgeschlagen
            self._connected = False
            logging.error(f"MQTT connect failed: rc={rc}")

    def _on_message(self, client, userdata, msg) -> None:
        topic = msg.topic
        payload = msg.payload.decode(errors="replace")
        logging.info(f"MQTT message recieved: topic='{topic}', payload='{payload}'")

        # Dispatch: 1) exakter Match, 2) wildcard-matches
        # paho liefert beim Subscribe mit Wildcards trotzdem msg.topic als exaktes Topic.
        # Deshalb muss man selbst wildcard-regeln prüfen.
        # für die Einfachheit unterstütze ich hier exact + "+" / "#" wildcards über mqtt.topic_matches_sub.
        for sub_topic, handler in self._handlers.items():
            if mqtt.topic_matches_sub(sub_topic, topic):
                handler(topic, payload)