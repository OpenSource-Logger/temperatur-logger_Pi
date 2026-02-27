# analysis.py
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

Point = Tuple[int, float]  # (ts, value)


def parse_time_expr(s: str, now_ts: Optional[int] = None) -> int:
    """
    Akzeptiert:
      - "now"
      - "now-6h", "now-15m", "now-2d"
      - ISO: "2026-02-26T10:00:00" (naive => lokale Zeit ist hier nicht bekannt; wir behandeln es als UTC)
      - Unix seconds: "1700000000"
      - Unix ms: "1700000000000"
    """
    s = (s or "").strip()
    if not s:
        raise ValueError("time expression leer")

    if now_ts is None:
        now_ts = int(datetime.now(tz=timezone.utc).timestamp())

    if s == "now":
        return now_ts

    m = re.fullmatch(r"now-(\d+)([smhd])", s)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        mul = {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]
        return now_ts - n * mul

    # numeric epoch
    if re.fullmatch(r"\d{10,13}", s):
        v = int(s)
        if len(s) == 13:
            return v // 1000
        return v

    # ISO
    try:
        dt = datetime.fromisoformat(s)
    except ValueError as e:
        raise ValueError(f"Ungültiges time format: {s}") from e

    # naive => UTC interpretieren
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def bucketize(points: Sequence[Point], bucket_s: int) -> List[Point]:
    """
    Gruppiert nach bucket (floor(ts/bucket_s)*bucket_s) und mittelt Werte pro Bucket.
    """
    if bucket_s <= 0:
        return list(points)

    acc: Dict[int, Tuple[float, int]] = {}
    for ts, v in points:
        b = (ts // bucket_s) * bucket_s
        s, c = acc.get(b, (0.0, 0))
        acc[b] = (s + float(v), c + 1)

    out = [(b, s / c) for b, (s, c) in acc.items()]
    out.sort(key=lambda x: x[0])
    return out


def moving_average(points: Sequence[Point], window_s: int) -> List[Point]:
    """
    Zeitfenster-basierter gleitender Mittelwert über die letzten window_s Sekunden.
    Erwartet sortierte Punkte.
    """
    if window_s <= 0:
        return list(points)

    out: List[Point] = []
    q: List[Point] = []
    sum_v = 0.0

    for ts, v in points:
        q.append((ts, v))
        sum_v += v

        cutoff = ts - window_s
        while q and q[0][0] < cutoff:
            t0, v0 = q.pop(0)
            sum_v -= v0

        out.append((ts, sum_v / max(1, len(q))))

    return out


def combine_add(series_list: Sequence[Sequence[Point]]) -> List[Point]:
    """
    Addiert mehrere Serien auf gemeinsamen Buckets.
    Erwartet, dass alle Serien bereits gebucketized sind und ts exakt matchen können.
    Nimmt die Vereinigungsmenge von Buckets und summiert, wenn Wert vorhanden.
    """
    m: Dict[int, float] = {}
    for series in series_list:
        for ts, v in series:
            m[ts] = m.get(ts, 0.0) + float(v)

    out = sorted(m.items(), key=lambda x: x[0])
    return [(ts, val) for ts, val in out]


def combine_sub(a: Sequence[Point], b: Sequence[Point]) -> List[Point]:
    """
    A - B auf Buckets. Nur dort, wo beide Werte existieren.
    """
    mb = {ts: v for ts, v in b}
    out: List[Point] = []
    for ts, va in a:
        if ts in mb:
            out.append((ts, float(va) - float(mb[ts])))
    return out


def quasi_peak(points: Sequence[Point], tau_charge_ms: int, tau_discharge_ms: int) -> List[Point]:
    """
    Quasi-Peak als asymmetrischer Exponentialdetektor:
      - bei x > y: tau_charge
      - bei x <= y: tau_discharge
    y[n] = y[n-1] + (x - y[n-1]) * alpha
    alpha = 1 - exp(-dt/tau)
    """
    if not points:
        return []

    tau_c = max(1, int(tau_charge_ms)) / 1000.0
    tau_d = max(1, int(tau_discharge_ms)) / 1000.0

    out: List[Point] = []
    y = float(points[0][1])
    prev_ts = int(points[0][0])
    out.append((prev_ts, y))

    for ts, x in points[1:]:
        ts = int(ts)
        x = float(x)
        dt = max(0.0, ts - prev_ts)

        tau = tau_c if x > y else tau_d
        alpha = 1.0 - math.exp(-dt / tau) if tau > 0 else 1.0

        y = y + (x - y) * alpha
        out.append((ts, y))
        prev_ts = ts

    return out


@dataclass(frozen=True)
class AnalysisRequest:
    device_ids: List[str]
    ts_from: int
    ts_to: int
    operation: str
    params: Dict[str, object]
    downsample_s: int = 1


@dataclass(frozen=True)
class AnalysisResponse:
    series: List[Point]
    scalar: Optional[float] = None