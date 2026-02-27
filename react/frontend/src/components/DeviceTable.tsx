import { useMemo, useState } from "react";
import type { Device } from "../types";
import { assignDeviceId, blink, setSensorType } from "../api";

const SENSOR_OPTIONS = [
  { value: "mcp9701a", label: "MCP9701A (linear)" },
  { value: "ntc_beta_divider", label: "NTC Beta (Divider)" },
  { value: "lut_v_to_c", label: "Lookup Table (V→°C)" },
  // später: pt100, thermocouple, ...
];

function fmtTs(ts: number) {
  const d = new Date(ts * 1000);
  return d.toLocaleString();
}

export function DeviceTable(props: { devices: Device[]; onRefresh: () => Promise<void> }) {
  const { devices, onRefresh } = props;

  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // lokale Eingaben pro Chip
  const [nameDraft, setNameDraft] = useState<Record<string, string>>({});

  async function doAssign(chipId: string) {
    const v = (nameDraft[chipId] ?? "").trim();
    if (!v) return;

    setBusyKey(`assign:${chipId}`);
    setError(null);
    try {
      await assignDeviceId(chipId, v);
      await onRefresh();
    } catch (e: any) {
      setError(e.message ?? String(e));
    } finally {
      setBusyKey(null);
    }
  }

  async function doSetSensor(deviceId: string, sensorType: string) {
    setBusyKey(`sensor:${deviceId}`);
    setError(null);
    try {
      await setSensorType(deviceId, sensorType, null);
      await onRefresh();
    } catch (e: any) {
      setError(e.message ?? String(e));
    } finally {
      setBusyKey(null);
    }
  }

  async function doBlink(deviceId: string) {
    setBusyKey(`blink:${deviceId}`);
    setError(null);
    try {
      await blink(deviceId, 2000, 200);
    } catch (e: any) {
      setError(e.message ?? String(e));
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <div style={{ border: "1px solid #ddd", padding: 12, borderRadius: 8 }}>
      <h3 style={{ marginTop: 0 }}>Geräte</h3>

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th style={{ textAlign: "left", borderBottom: "1px solid #eee", padding: 8 }}>Chip-ID</th>
            <th style={{ textAlign: "left", borderBottom: "1px solid #eee", padding: 8 }}>IP</th>
            <th style={{ textAlign: "left", borderBottom: "1px solid #eee", padding: 8 }}>Device_ID (Name)</th>
            <th style={{ textAlign: "left", borderBottom: "1px solid #eee", padding: 8 }}>LED</th>
            <th style={{ textAlign: "left", borderBottom: "1px solid #eee", padding: 8 }}>Sensortyp</th>
            <th style={{ textAlign: "left", borderBottom: "1px solid #eee", padding: 8 }}>Last Seen</th>
          </tr>
        </thead>
        <tbody>
          {devices.map((d) => {
            const assigned = !!d.device_id;
            const keyAssign = `assign:${d.chip_id}`;
            const keyBlink = d.device_id ? `blink:${d.device_id}` : "";
            const keySensor = d.device_id ? `sensor:${d.device_id}` : "";

            return (
              <tr key={d.chip_id}>
                <td style={{ padding: 8, borderBottom: "1px solid #f3f3f3" }}>{d.chip_id}</td>
                <td style={{ padding: 8, borderBottom: "1px solid #f3f3f3" }}>{d.ip_last ?? "-"}</td>

                <td style={{ padding: 8, borderBottom: "1px solid #f3f3f3" }}>
                  {!assigned ? (
                    <div style={{ display: "flex", gap: 8 }}>
                      <input
                        placeholder="z.B. Wohnzimmer"
                        value={nameDraft[d.chip_id] ?? ""}
                        onChange={(e) => setNameDraft((s) => ({ ...s, [d.chip_id]: e.target.value }))}
                      />
                      <button onClick={() => doAssign(d.chip_id)} disabled={busyKey === keyAssign}>
                        Set
                      </button>
                    </div>
                  ) : (
                    <span>{d.device_id}</span>
                  )}
                </td>

                <td style={{ padding: 8, borderBottom: "1px solid #f3f3f3" }}>
                  <button
                    onClick={() => d.device_id && doBlink(d.device_id)}
                    disabled={!d.device_id || busyKey === keyBlink}
                  >
                    Blink
                  </button>
                </td>

                <td style={{ padding: 8, borderBottom: "1px solid #f3f3f3" }}>
                  <select
                    disabled={!d.device_id || busyKey === keySensor}
                    value={d.sensor_type ?? ""}
                    onChange={(e) => d.device_id && doSetSensor(d.device_id, e.target.value)}
                  >
                    <option value="" disabled>
                      (wählen)
                    </option>
                    {SENSOR_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                </td>

                <td style={{ padding: 8, borderBottom: "1px solid #f3f3f3" }}>{fmtTs(d.last_seen)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {error && <div style={{ color: "crimson", marginTop: 8 }}>{error}</div>}
    </div>
  );
}