# main.py
from __future__ import annotations

import uvicorn
import logging

from config import CFG
from db import Database
from mqtt_client import MqttClient, MqttSettings
from provisioning import ProvisioningService
from sensors_service import SensorService, AdcSettings
from ingest import IngestService
from commands import CommandService
from api import create_app, ApiDependencies

logging.basicConfig(level=logging.INFO)

def build_services():
    # DB
    db = Database(CFG.db.path)
    db.connect()

    # MQTT
    mqtt_settings = MqttSettings(
        host = CFG.mqtt.host,
        port = CFG.mqtt.port,
        keepalive = CFG.mqtt.keepalive,
        client_id = CFG.mqtt.client_id,
    )
    mqtt = MqttClient(mqtt_settings)

    # Services
    provisioning = ProvisioningService(db=db, mqtt=mqtt, server_name=CFG.server_name)

    sensors = SensorService(
        db=db,
        adc=AdcSettings(bits=CFG.adc.bits, vref=CFG.adc.v_ref),
    )

    ingest = IngestService(db=db, mqtt=mqtt, sensors=sensors, server_name=CFG.server_name)

    commands = CommandService(mqtt=mqtt, server_name=CFG.server_name)

    # MQTT Subscriptions registrieren (vor connect ist ok)
    provisioning.register_subscriptions()
    ingest.register_subscriptions()

    return db, mqtt, provisioning, sensors, ingest, commands

def main() -> None:
    db, mqtt, provisioning, sensors, ingest, commands = build_services()

    # MQTT starten
    mqtt.connect_and_start()

    # FastAPI App
    deps = ApiDependencies(db=db, provisioning=provisioning, commands=commands, sensors=sensors)
    app = create_app(deps)


    try:
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
    finally:
        # Shutdown
        mqtt.stop_and_disconnect()
        db.close()

if __name__ == "__main__":
    main()