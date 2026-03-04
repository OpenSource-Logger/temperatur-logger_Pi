# config.py
from __future__ import annotations

from dataclasses import dataclass



@dataclass(frozen=True)
class MqttConfig:
    host: str = "127.0.0.1"
    port: int = 1883
    keepalive: int = 60
    client_id: str = "temp-logger-backend"


@dataclass(frozen=True)
class DbConfig:
    path: str = "/var/lib/temperatur-logger_Pi/measurements.db"


@dataclass(frozen=True)
class AdcConfig:
    bits: int = 12
    v_ref: float = 3.3


@dataclass(frozen=True)
class AppConfig:
    # <Server>-Prefix in den Topics
    server_name: str = "Server1"

    mqtt: MqttConfig = MqttConfig()
    db: DbConfig = DbConfig()
    adc: AdcConfig = AdcConfig()


CFG = AppConfig()


class Topics:
    """
    Topic-Builder. Enthält nur string-templates.
    Hängt ab vom server_name
    """

    # Discovery: ESP -> Server (noch ohne Devide_ID)
    DISCOVERY_HELLO = "{server}/discovery/hello"                # publish vom ESP
    DISCOVERY_ACK = "{server}/discovery/ack/{device_id}"        # publish vom Server

    # Messwerte: ESP -> Server
    ADC = "{server}/{device_id}/adc"                            # publish vom ESP

    # Commands: Server -> ESP
    CMD_LED = "{server}/{device_id}/cmd/led"                    # publish vom Server
    CMD_MEASURE_GLOBAL = "{server}/cmd/measure"                 # publish vom Server

    # Optional: Status/Heartbeat
    STATUS = "{server}/{device_id}/status"

    @staticmethod
    def discovery_hello(server: str) -> str:
        return Topics.DISCOVERY_HELLO.format(server=server)
    
    @staticmethod
    def discovery_ack(server: str, chip_id: str) -> str:
        return Topics.DISCOVERY_ACK.format(server=server, chip_id=chip_id)
    
    @staticmethod
    def adc(server: str, device_id: str) -> str:
        return Topics.ADC.format(server=server, device_id=device_id)
    
    @staticmethod
    def cmd_led(server: str, device_id: str) -> str:
        return Topics.CMD_LED.format(server=server, device_id=device_id)
    
    @staticmethod
    def cmd_measure_global(server: str) -> str:
        return Topics.CMD_MEASURE_GLOBAL.format(server=server)
    
    @staticmethod
    def status(server: str, device_id: str) -> str:
        return Topics.STATUS.format(server=server, device_id=device_id)
    
    @staticmethod
    def adc_wildcard(server: str) -> str:
        # subscribed alle ADC Topics: Server1/+/adc
        return f"{server}/+/adc"