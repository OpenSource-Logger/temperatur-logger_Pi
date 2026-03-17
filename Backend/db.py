# db.py
from __future__ import annotations

import sqlite3
import threading
import time
import logging
from dataclasses import dataclass
from typing import List, Optional

@dataclass(frozen=True)
class DeviceRow:
    chip_id: str
    ip_last: Optional[str]
    device_id: Optional[str]
    sensor_type: Optional[str]
    sensor_params: Optional[str]
    created_at: int
    last_seen: int


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        self.conn: Optional[sqlite3.Connection] = None
        self._lock = threading.Lock()

    def connect(self) -> None:
        if self.conn is not None:
            return
        
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")

        self._init_schema()

    def _init_schema(self) -> None:
        assert self.conn is not None

        with self._lock:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS devices (
                    chip_id         TEXT PRIMARY KEY,
                    ip_last         TEXT,
                    device_id       TEXT UNIQUE,
                    sensor_type     TEXT,
                    sensor_params   TEXT,
                    created_at      INTEGER NOT NULL,
                    last_seen       INTEGER NOT NULL
                );
                """
            )

            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS measurements (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts              INTEGER NOT NULL,
                    device_id       TEXT NOT NULL,
                    adc_raw         INTEGER,
                    temp_c          REAL NOT NULL
                );
                """
            )

            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_measurements_device_ts ON measurements (device_id, ts);"
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_measurements_ts ON measurements(ts);"
            )

            self.conn.commit()

# ---------------Device operations----------------

    def upsert_device_seen(self, chip_id: str, ip: Optional[str], ts: Optional[int] = None) -> None:
        logging.info(f"DB upser_device_seen called: chip_id='{chip_id}', ip='{ip}'")
        """
        Wird bei Discovery 'hello' genutzt:
        - legt Gerät an, falls neu
        - aktualisiert ip_last und last_seen
        """
        assert self.conn is not None
        now = int(time.time()) if ts is None else int(ts)

        with self._lock:
            # SQLite UPSERT (ON CONFLICT) auf PRIMARY KEY chip_id
            self.conn.execute(
                """
                INSERT INTO devices(chip_id, ip_last, created_at, last_seen)
                VALUES(?, ?, ?, ?)
                ON CONFLICT(chip_id) DO UPDATE SET
                    ip_last=excluded.ip_last,
                    last_seen=excluded.last_seen;
                """,
            (chip_id, ip, now, now),
            )
            self.conn.commit()
            logging.info(f"DB upsert successful for chip_id='{chip_id}'")

    def assign_device_id(self, chip_id: str, device_id: str) -> None:
        """
        UI-Aktion: Chip bekommt einen Namen (=Device_ID)
        """
        assert self.conn is not None
        now = int(time.time())

        with self._lock:
            self.conn.execute(
                """
                UPDATE devices
                SET device_id = ?, last_seen = ?
                WHERE chip_id = ?;
                """,
                (device_id, now, chip_id),
            )
            self.conn.commit()

    def set_sensor_type(self, device_id: str, sensor_type: str, sensor_params: Optional[str] = None) -> None:
        """
        UI-Aktion: Sensor-Typ für ein Device setzen.
        device_id muss existieren.
        """
        assert self.conn is not None
        now = int(time.time())

        with self._lock:
            self.conn.execute(
                """
                UPDATE devices
                SET sensor_type = ?, sensor_params = ?, last_seen = ?
                WHERE device_id = ?;
                """,
                (sensor_type, sensor_params, now, device_id),
            )
            self.conn.commit()
    
    def get_device_by_chip(self, chip_id: str) -> Optional[DeviceRow]:
        assert self.conn is not None
        cur = self.conn.execute("SELECT * FROM devices WHERE chip_id = ?;", (chip_id,))
        row = cur.fetchone()
        return self._row_to_device(row) if row else None
    
    def get_device_by_device_id(self, device_id: str) -> Optional[DeviceRow]:
        assert self.conn is not None
        cur = self.conn.execute("SELECT * FROM devices WHERE device_id = ?;", (device_id,))
        row = cur.fetchone()
        return self._row_to_device(row) if row else None
    
    def list_devices(self) -> List[DeviceRow]:
        assert self.conn is not None
        cur = self.conn.execute("SELECT * FROM devices ORDER BY last_seen DESC;")
        return [self._row_to_device(r) for r in cur.fetchall()]
    
    def _row_to_device(self, r: sqlite3.Row) -> DeviceRow:
        return DeviceRow(
            chip_id=str(r["chip_id"]),
            ip_last=r["ip_last"],
            device_id=r["device_id"],
            sensor_type=r["sensor_type"],
            sensor_params=r["sensor_params"],
            created_at=int(r["created_at"]),
            last_seen=int(r["last_seen"]),
        )
    
# ---------------Measurement operations----------------

    def insert_measurement(
            self,
            device_id: str,
            temp_c: float,
            adc_raw: Optional[int] = None,
            ts: Optional[int] = None,
    ) -> None:
        """
        Messpunkt speichern. ts default: jetzt
        """
        assert self.conn is not None
        now = int(time.time()) if ts is None else int(ts)

        with self._lock:
            self.conn.execute(
                """
                INSERT INTO measurements (ts, device_id, adc_raw, temp_c)
                VALUES (?, ?, ?, ?);
                """,
                (now, device_id, adc_raw, float(temp_c)),
            )
            self.conn.commit()
            logging.info(f"DB insert successful for device_id: '{device_id}'")

    def fetch_measurements(self, device_id: str, ts_from: int, ts_to: int) -> list[tuple[int, float]]:
        """
        Liefert (ts, temp_c) sortiert.
        """
        assert self.conn is not None
        with self._lock:
            cur = self.conn.execute(
                """
                SELECT ts, temp_c
                FROM measurements
                WHERE device_id = ? AND ts >= ? AND ts <= ?
                ORDER BY ts ASC;
                """,
                (device_id, int(ts_from), int(ts_to)),
            )
            rows = cur.fetchall()
        return [(int(r[0]), float(r[1])) for r in rows]

    def close(self) -> None:
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def __enter__(self) -> "Database":
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()