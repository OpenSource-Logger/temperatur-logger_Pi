import paho.mqtt.client as mqtt

class MqttSubscriber:
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
        self.topic: str | None = None

        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id or "",
        )
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message

    def subscribe(self, topic: str, qos: int = 0) -> None:
        """Topic setzen und Verbindung starten"""
        self.topic = topic
        self.qos = qos
        self._client.connect(self.broker, self.port, self.keepalive)
        self._client.loop_start()

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            print("Verbunden")
            if self.topic is not None:
                client.subscribe(self.topic, qos=self.qos)
        else:
            print("Verbindung fehlgeschlagen:", rc)
    
    def _on_message(self, client, userdata, msg):
        payload = msg.payload.decode(errors="replace")
        print(f"{msg.topic}: {payload}")

    def close(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()
    
    def __enter__(self) -> MqttSubscriber:
        return self
    
    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()