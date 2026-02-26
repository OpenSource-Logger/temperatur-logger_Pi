# commands.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from config import CFG, Topics
from mqtt_client import MqttClient

@dataclass
class CommandService:
    mqtt: MqttClient
    server_name: str = CFG.server_name

    # ----- LED (pro Device) -----

    def blink_led(self, device_id: str, duration_ms: int = 2000, period_ms: int = 200) -> None:
        """
        Sendet LED-Blink Kommando an ein Device
        """
        topic = Topics.cmd_led(self.server_name, device_id)
        payload = {
            "mode": "blink",
            "duration_ms": int(duration_ms),
            "period_ms": int(period_ms)
        }
        self.mqtt.publish_json(topic, payload, qos=0, retain=False)
    
    # ----- Measurement control (global, für alle ESP) -----

    def start_measurement_all(
            self,
            interval_s: int,
            count: Optional[int] = None,
            duration_s: Optional[int] = None
    ) -> None:
        """
        Startet die Messreihe auf allen ESP gleichzeitig.
        Entweder count ODER duration_s setzen (nur eins).
        """
        if (count is None) == (duration_s is None):
            raise ValueError("Entweder count oder duration_s setzen (nur eins).")
        
        topic = Topics.cmd_measure_global(self.server_name)
        payload = {"action": "start", "interval_s": int(interval_s)}
        if count is not None:
            payload["count"] = int(count)
        if duration_s is not None:
            payload["duration_s"] = int(duration_s)
        
        self.mqtt.publish_json(topic, payload, qos=0, retain=False)

    def pause_measurement_all(self) -> None:
        topic = Topics.cmd_measure_global(self.server_name)
        self.mqtt.publish_json(topic, {"action": "pause"}, qos=0, retain=False)

    def stop_measurement_all(self) -> None:
        topic = Topics.cmd_measure_global(self.server_name)
        self.mqtt.publish_json(topic, {"action": "stop"}, qos=0, retain=False)