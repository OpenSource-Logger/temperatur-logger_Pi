# api.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

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
    provisioning = ProvisioningService
    commands: CommandService


def create_app(deps: ApiDependencies) -> FastAPI:
    app = FastAPI(title= "Temperatur-Logger API")


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
    
    return app