# sensors_service.py
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from db import Database
from sensors_models import (
    SensorModel,
    LinearVoltageModel,
    NtcBetaDividerModel,
    LookupTableVoltageModel,
)


@dataclass(frozen=True)
class AdcSettings:
    bits: int
    vref: float


class SensorFactory:
    """
    Baut SensorModel-Instanzen aus sensor_type + optionalen Parametern.
    sensor_params ist ein JSON-String (oder None).
    """
    def __init__(self, adc_vref: float) -> None:
        self.adc_vref = float (adc_vref)

    def build(self, sensor_type: str, sensor_params: Optional[str]) -> SensorModel:
        st = sensor_type.strip().lower()

        params: dict = {}
        if sensor_params:
            try:
                params = json.loads(sensor_params)
                if not isinstance(params, dict):
                    params = {}
            except json.JSONDecodeError:
                params = {}

        # ---- lineare Sensoren ----
        if st == "mcp9701a":
            # typisch: 400mV @ 0°C, 19,5mV/°C
            v0 = float(params.get("v0_v", 0.400))
            slope = float(params.get("slope_v_per_c", 0.0195))
            return LinearVoltageModel(v0_v=v0, slope_v_per_c=slope)
        
        # ---- NTC Beta Divider ----
        if st == "ntc_beta_divider":
            # expected params: r_fixed_ohm, r0_ohm, t0_c, beta_k, wiring
            return NtcBetaDividerModel(
                v_ref=self.adc_vref,
                r_fixed_ohm=float(params.get("r_fixed_ohm", 10_000.0)),
                r0_ohm=float(params.get("r0_ohm", 10_000.0)),
                t0_c=float(params.get("t0_c", 25.0)),
                beta_k=float(params.get("beta_k", 3950.0)),
                wiring=str(params.get("wiring", "ntc_to_gnd")),
            )
        
        # ---- Lookup Table ----
        if st == "lut_v_to_v":
            # params: points = [[v,c], [v,c], ...]
            points = params.get("points", [])
            pts_t: Tuple[Tuple[float, float], ...] = tuple((float(v), float(c)) for v, c in points)
            return LookupTableVoltageModel(points_v_to_c=pts_t)
        
        raise KeyError(f"Unbekannter sensor_type: {sensor_type!r}")
    

@dataclass
class SensorService:
    """
    API:
        - temperature_from_adc(device_id, adc_raw) -> float
        
    sensor_type und params kommen aus DB (devices.sensor_type / sensor_params).
    """
    db: Database
    adc: AdcSettings

    def __post_init__(self) -> None:
        self._factory = SensorFactory(adc_vref=self.adc.vref)
        self._cache: Dict[str, Tuple[Optional[str], SensorModel]] = {}
        # cache-key: device_id -> (sensor_type, sensor_params, model)

    def adc_to_voltage(self, adc_raw: int) -> float:
        max_adc = (1 << int(self.adc.bits)) - 1
        if adc_raw < 0 or adc_raw > max_adc:
            raise ValueError(f"ADC außerhalb Range: {adc_raw} (0..{max_adc})")
        return float(adc_raw) * float(self.adc.vref) / float(max_adc)
    
    def _get_model_for_device(self, device_id: str) -> SensorModel:
        # DB lookup
        dev = self.db.get_device_by_device_id(device_id)
        if dev is None:
            raise KeyError(f"Unbekannte Device_ID: {device_id}")
        if not dev.sensor_type;
            raise KeyError(f"Kein sensor_type gesetzt für device_id: {device_id}")
        
        sensor_type = dev.sensor_type
        sensor_params = dev.sensor_params

        # Cache hit?
        cached = self._cache.get(device_id)
        if cached and cached[0] == sensor_type and cached [1] == sensor_params:
            return cached[2]
        
        model = self._factory.build(sensor_type, sensor_params)
        self._cache[device_id] = (sensor_type, sensor_params, model)
        return model
    
    def temperature_from_adc(self, device_id: str, adc_raw: int) -> float:
        model = self._get_model_for_device(device_id)
        v = self.adc_to_voltage(adc_raw)
        return float(model.temperature_c(v))
    
    def invalidate_cache_for_device(self, device_id: str) -> None:
        """
        Aufrufen, wenn UI den Sensortyp ändert.
        """
        self._cache.pop(device_id, None)