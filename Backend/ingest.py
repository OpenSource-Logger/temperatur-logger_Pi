# ingest.py
from __future__ import annotations

import time
from dataclasses import dataclass

from config import CFG, Topics
from db import Database
from mqtt_client import MqttClient
from sensors_service import SensorService


@dataclass
class IngestService:
    db: Database
    mqtt: MqttClient
    sensors: SensorService
    server_name: str = CFG.server_name

    def register_subscriptions(self) -> None:
        # subscribt alle Devices: Server1/+/adc
        self.mqtt.subscribe(Topics.adc_wildcard(self.server_name), self.on_adc_message, qos=0)

    def on_adc_message(self, topic: str, payload: str) -> None:
        """
        Topic: <server>/<device_id>/adc
        Payload: adc_raw als int (z.B. "2048")
        """
        try:
            device_id = self._device_id_from_adc_topic(topic)
            adc_raw = self._parse_adc(payload)
            temp_c = self.sensors.temperature_from_adc(device_id=device_id, adc_raw=adc_raw)

            # ts: serverseitig "jetzt" (oder optional aus payload)
            self.db.insert_measurement(device_id=device_id, temp_c=temp_c, adc_raw=adc_raw, ts=int(time.time()))
        except Exception as e:
            print(f"Ingest-Fehler: topic={topic} payload={payload!r}: {e}")

    def _device_id_from_adc_topic(self, topic: str) -> str:
        parts = topic.split("/")
        # erwartet: [server, device_id, "adc"]
        if len(parts) != 3:
            raise ValueError(f"Unerwartetes Topic-Format: {topic}")
        server, device_id, func = parts
        if server != self.server_name:
            raise ValueError(f"Falscher Server-Prefix: {server} != {self.server_name}")
        if func != "adc":
            raise ValueError(f"Falsche Funktion: {func}")
        if not device_id:
            raise ValueError("device_id ist leer")
        return device_id
    
    def _parse_adc(self, payload: str) -> int:
        return int(payload.strip())