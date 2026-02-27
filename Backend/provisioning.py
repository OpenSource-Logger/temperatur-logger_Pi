# provisioning.py
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from config import CFG, Topics
from db import Database
from mqtt_client import MqttClient


@dataclass
class ProvisioningService:
    """
    - verarbeitet Discovery Hello Nachrichten
    - sendet Ack (Device_Id) an ein bestimmtes Gerät 8chip_id)
    """
    db: Database
    mqtt: MqttClient
    server_name: str = CFG.server_name

    def register_subscriptions(self) -> None:
        hello_topic = Topics.discovery_hello(self.server_name)
        self.mqtt.subscribe(hello_topic, self.on_discovery_hello, qos=0)

    def on_discovery_hello(self, topic: str, payload: str) -> None:
        """
        Erwartete Payload:
        {"chip_id: "...", "ip": "...", "fw": "..."}
        Minimal: chip_id und ip.
        """
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            # Fallback: falls erstmal nur die IP gesendet wird
            # dann fehlt chip_id -> ohne chip_id kann das Gerät nicht eindeutig identifiziert werden
            print(f"Discovery hello: ungültiges JSON: {payload!r}")
            return
        
        chip_id = str(data.get("chip_id") or "").strip()
        ip = data.get("ip")
        ip_str: Optional[str] = str(ip).strip() if ip is not None else None

        if not chip_id:
            print(f"Discovery hello: chip_id fehlt: {payload!r}")
            return
        
        # Gerät als "gesehen" speichern/aktualisieren
        self.db.upsert_device_seen(chip_id=chip_id, ip=ip_str)

        # prüfen ob device_id bereits vergeben ist,
        # dann automatisch nochmal ack senden (z.B. nach Neustart des ESP)
        dev = self.db.get_device_by_chip(chip_id)
        if dev and dev.device_id:
            self.send_ack(chip_id=chip_id, device_id=dev.device_id)

    
    def send_ack(self, chip_id: str, device_id: str) -> None:
        """
        Sendet Device_ID an genau dieses Gerät.
        ESP subcsribt: <server>/discovery/ack/<chip_id>
        """
        ack_topic = Topics.discovery_ack(self.server_name, chip_id)
        self.mqtt.publish_json(ack_topic, {"device_id": device_id}, qos=0, retain=False)


    def assign_device_id_and_ack(self, chip_id: str, device_id: str) -> None:
        """
        Wird später aus der API heraus aufgerufen, wenn im UI der Name gesetzt wird.
        - persistiert device_id
        - sendet ack an das Gerät
        """
        self.db.assign_device_id(chip_id=chip_id, device_id=device_id)
        self.send_ack(chip_id=chip_id, device_id=device_id)