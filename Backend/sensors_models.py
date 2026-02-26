# sensors_models.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Tuple
import bisect
import math

class SensorModel(Protocol):
    def temperature_c(self, voltage_v: float) -> float: ...


# ---------- Lineare Sensoren ----------

@dataclass(frozen=True)
class LinearVoltageModel:
    """
    Vout = v0 + slope * T => T = (Vout - v0) / slope
    MCP9701A typisch: v0 = 0.400V @ 0°C, slope = 0.0195 V/°C
    """
    v0_v: float
    slope_v_per_c: float

    def temperature_c(self, voltage_v: float) -> float:
        return float((float(voltage_v) - self.v0_v) / self.slope_v_per_c)
    

# ---------- Lookup-Tabellen (piecewise linear) ----------

@dataclass(frozen=True)
class LookupTableVoltageModel:
    """
    Piecewise-linear Kennlinie: Punkte (V -> °C).
    für Sensor/Verstärker-Ketten oder Thermoelemente

    points_v_to_c: Sequenz von (V, °C), wird intern nach V sortiert
    """
    points_v_to_c: Tuple[Tuple[float, float], ...]

    def __post_init__(self) -> None:
        pts = tuple(sorted(self.points_v_to_c, key=lambda x: x[0]))
        object.__setattr__(self, "points_v_to_c", pts)

    def temperature_c(self, voltage_v: float) -> float:
        pts = self.points_v_to_c
        if len(pts) < 2:
            raise ValueError("LookupTable benötigt mindestens 2 Punkte")
        
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]

        v = float(voltage_v)

        # Clamp außerhalb der Range
        if v <= xs[0]:
            return float(ys[0])
        if v >= xs[-1]:
            return float(ys[-1])
        
        i = bisect.bisect_right(xs, v)
        x0, y0 = xs[i-1], ys[i-1]
        x1, y1 = xs[i], ys[i]

        t = (v - x0) / (x1 - x0)
        return float(y0 + t * (y1 - y0))
    

# ---------- NTC (Beta) im Spannungsteiler ----------

@dataclass(frozen=True)
class NtcBetaDividerModel:
    """
    NTC Beta-Modell in Spannungsteiler.
    Erwartet Vout am ADC-Knoten.
    wiring:
        - "ntc_to_gnd": NTC nach GND, Rfixed nach Vref (Vout steigt mit Temp abhängig vom NTC)
            Vout = Vref * Rntc / (Rntc + Rfixed)
        - "ntc_to_vref": NTC nach Vref, Rfixed nach GND 
            Vout = Vref * Rfixed / (Rntc + Rfixed)
    """
    v_ref: float
    r_fixed_ohm: float
    r0_ohm: float = 10_000.00
    t0_c: float = 25.0
    beta_k: float = 3950.0
    wiring: str = "ntc_to_gnd"

    def temperature_c(self, voltage_v: float) -> float:
        v = float(voltage_v)
        if v <= 0.0:
            raise ValueError("Spannung <=0 nicht auswertbar.")
        if v >= self.v_ref:
            raise ValueError("Spannung >= Vref nicht auswertbar.")
        
        if self.wiring == "ntc_to_gnd":
            r_ntc = self.r_fixed_ohm * v / (self.v_ref - v)
        elif self.wiring == "ntc_to_vref":
            r_ntc = self.r_fixed_ohm * (self.v_ref - v) / v
        else:
            raise ValueError(f"Unbekanntes wiring: {self.wiring}")
        
        if r_ntc <= 0.0:
            raise ValueError("Berechneter NTC-Widerstand unplausibel.")
        
        t0_k = self.t0_c + 273.15
        inv_t = (1.0/t0_k) + (1.0 / self.beta_k) * math.log(r_ntc / self.r0_ohm)
        t_k = 1.0 / inv_t
        return float(t_k - 273.15)