# api.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from fastapi.middleware.cors import CORSMiddleware

from analysis import (
    AnalysisRequest,
    AnalysisResponse,
    bucketize,
    combine_add,
    combine_sub,
    moving_average,
    parse_time_expr,
    quasi_peak,
)

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from db import Database
from provisioning import ProvisioningService
from commands import CommandService


# ---------- Request/Response Models ----------

class AssignDeviceIdRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)


class SetSensorTypeRequest(BaseModel):
    sensor_type: str = Field(min_length=1, max_length=64)
    sensor_params: Optional[str] = None # JSON string optional


class BlinkRequest(BaseModel):
    duration_ms: int = 2000
    period_ms: int = 200


class MeasureStartRequest(BaseModel):
    interval_s: int = Field(gt=0)
    count: Optional[int] = Field(default=None, gt=0)
    duration_s: Optional[int] = Field(default=None, gt=0)


@dataclass
class ApiDependencies:
    db: Database
    provisioning: ProvisioningService
    commands: CommandService

class AnalysisSeriesRequest(BaseModel):
    device_ids: List[str]
    from_: str = Field(alias="from")
    to: str
    operation: str
    params: Dict[str, Any] = {}
    downsample_s: int = 1


def create_app(deps: ApiDependencies) -> FastAPI:
    app = FastAPI(title= "Temperatur-Logger API")

    app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----- Devices -----

    @app.get("/devices")
    def list_devices():
        return [
            {
                "chip_id": d.chip_id,
                "ip_last": d.ip_last,
                "device_id": d.device_id,
                "sensor_type": d.sensor_type,
                "sensor_params": d.sensor_params,
                "created_at": d.created_at,
                "last_seen": d.last_seen,
            }
            for d in deps.db.list_devices()
        ]
    
    @app.post("/devices/{chip_id}/assign")
    def assign_device_id(chip_id: str, req: AssignDeviceIdRequest):
        dev = deps.db.get_device_by_chip(chip_id)
        if dev is None:
            raise HTTPException(status_code=404, detail="chip_id unbekannt")
        
        # persist -> ack an Gerät
        try:
            deps.provisioning.assign_device_id_and_ack(chip_id=chip_id, device_id=req.device_id)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        return {"ok": True}
    
    @app.post("/devices/{device_id}/sensor")
    def set_sensor_type(device_id: str, req: SetSensorTypeRequest):
        dev = deps.db.get_device_by_device_id(device_id)
        if dev is None:
            raise HTTPException(status_code=404, detail="device_id unbekannt")

        deps.db.set_sensor_type(device_id=device_id, sensor_type=req.sensor_type, sensor_params=req.sensor_params)
        deps.sensors.invalidate_cache_for_device(device_id)
        return {"ok": True}
    
    @app.post("/devices/{device_id}/blink")
    def blink_device_led(device_id: str, req: BlinkRequest):
        dev = deps.db.get_device_by_device_id(device_id)
        if dev is None:
            raise HTTPException(status_code=404, detail="device_id unbekannt")

        deps.commands.blink_led(
            device_id=device_id,
            duration_ms=req.duration_ms,
            period_ms=req.period_ms,
        )
        return {"ok": True}
    
    # ----- Measurement control (global) -----

    @app.post("/measure/start")
    def measure_start(req: MeasureStartRequest):
        # genau eins von count/duration_s
        if (req.count is None) == (req.duration_s is None):
            raise HTTPException(status_code=400, detail="Entweder count ODER durations_s setzen")
        
        try:
            deps.commands.start_measurement_all(
                interval_s=req.interval_s,
                count=req.count,
                duration_s=req.duration_s,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        return {"ok": True}
    
    @app.post("/measure/pause")
    def measure_pause():
        deps.commands.pause_measurement_all()
        return {"ok": True}
    
    @app.post("/measure/stop")
    def measure_stop():
        deps.commands.stop_measurement_all()
        return {"ok": True}
    
    @app.post("/analysis/series")
    def analysis_series(req: AnalysisSeriesRequest):
        ts_from = parse_time_expr(req.from_)
        ts_to = parse_time_expr(req.to)
        if ts_to < ts_from:
            raise HTTPException(status_code=400, detail="to < from")

        device_ids = [x for x in req.device_ids if x]
        if not device_ids:
            raise HTTPException(status_code=400, detail="device_ids leer")

        op = req.operation.strip().lower()
        ds = int(req.downsample_s or 1)

        # Fetch + bucketize pro device
        per_device: list[tuple[str, list[tuple[int, float]]]] = []
        for did in device_ids:
            pts = deps.db.fetch_measurements(did, ts_from, ts_to)
            pts_b = bucketize(pts, ds)
            per_device.append((did, pts_b))

        scalar = None

        # --- RAW: alle Serien zurückgeben ---
        if op == "raw":
            return {
                "series_list": [
                    {"name": did, "series": [{"ts": ts, "value": float(v)} for ts, v in pts]}
                    for did, pts in per_device
                ],
                "scalar": None,
            }

        # Ab hier: wir rechnen eine Ergebnis-Serie (eine Linie)
        base = per_device[0][1] if per_device else []

        if op == "mean":
            window_s = int(req.params.get("window_s", 10))
            out_series = moving_average(base, window_s)

        elif op == "add":
            out_series = combine_add([pts for _, pts in per_device])

        elif op == "sub":
            if len(per_device) < 2:
                raise HTTPException(status_code=400, detail="sub braucht mindestens 2 device_ids")
            out_series = combine_sub(per_device[0][1], per_device[1][1])

        elif op == "peak":
            scalar = max((v for _, v in base), default=None)
            out_series = base  # optional: wieder die Basis-Serie plotten

        elif op == "quasipeak":
            tau_c = int(req.params.get("tau_charge_ms", 500))
            tau_d = int(req.params.get("tau_discharge_ms", 1500))
            out_series = quasi_peak(base, tau_c, tau_d)

        else:
            raise HTTPException(status_code=400, detail=f"unknown operation: {req.operation!r}")

        return {
            "series_list": [
                {"name": op, "series": [{"ts": ts, "value": float(v)} for ts, v in out_series]}
            ],
            "scalar": scalar,
        }
    
    return app