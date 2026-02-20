from __future__ import annotations

import time
import paho.mqtt.client as mqtt

class MqttPublisher:
    def __init__(
            self,
            broker: str = "localhost",
            port: int = 1883,
            keepalive: int = 60,
            client_id: str | None = None,
    ) -> None:
        self.broker = broker
        self.port = port
        self.keepalive = keepalive

        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id or "",
        )
        self._client.connect(self.broker, self.port, self.keepalive)
        self._client.loop_start()

    def publish(self, topic: str, message: str, qos: int = 0, retain: bool = False) -> None:
        """
        Sendet eine MQTT-Nachricht. Wirft RuntimeError, wenn publish fehlschlägt.
        """

        info = self._client.publish(topic, message, qos=qos, retain=retain)
        info. wait_for_publish()

        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"Publish fehlgeschlagen, rc={info.rc}")
        
        # optional: kurzer Puffer, damit der Socket sauber flushen kann
        time.sleep(0.05)

    def close(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()

    # optional: damit "with MqttPublisher() as publisher:" funktioniert
    def __enter__(self) -> MqttPublisher:
        return self
    
    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()