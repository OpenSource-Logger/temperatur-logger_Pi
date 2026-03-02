import type { Device } from "../types";
import type { AnalysisOperation } from "../api";

type Props = {
  devices: Device[];
  selectedDeviceIds: string[];
  onSelectedDeviceIdsChange: (ids: string[]) => void;

  from: string;
  to: string;
  onFromToChange: (from: string, to: string) => void;

  operation: AnalysisOperation;
  onOperationChange: (op: AnalysisOperation) => void;

  meanWindowS: number;
  onMeanWindowSChange: (v: number) => void;

  qpChargeMs: number;
  qpDischargeMs: number;
  onQpParamsChange: (c: number, d: number) => void;
};

export function AnalysisControls(p: Props) {
  const ids = p.devices.map(d => d.device_id).filter((x): x is string => !!x);

  function toggle(id: string) {
    if (p.selectedDeviceIds.includes(id)) p.onSelectedDeviceIdsChange(p.selectedDeviceIds.filter(x => x !== id));
    else p.onSelectedDeviceIdsChange([...p.selectedDeviceIds, id]);
  }

  return (
    <div style={{ border: "1px solid #ddd", padding: 12, borderRadius: 8, marginTop: 12 }}>
      <h3 style={{ marginTop: 0 }}>Analyse</h3>

      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
        <label>
          from&nbsp;
          <input value={p.from} onChange={(e) => p.onFromToChange(e.target.value, p.to)} placeholder="now-6h oder ISO" />
        </label>
        <label>
          to&nbsp;
          <input value={p.to} onChange={(e) => p.onFromToChange(p.from, e.target.value)} placeholder="now oder ISO" />
        </label>

        <label>
          Operation&nbsp;
          <select value={p.operation} onChange={(e) => p.onOperationChange(e.target.value as AnalysisOperation)}>
            <option value="raw">Raw (pro Device)</option>
            <option value="mean">Mittelwert (Window)</option>
            <option value="add">Addieren (Summe)</option>
            <option value="sub">Subtrahieren (A-B)</option>
            <option value="peak">Peak (Max)</option>
            <option value="quasipeak">Quasi-Peak</option>
          </select>
        </label>

        {p.operation === "mean" && (
          <label>
            window_s&nbsp;
            <input
              type="number"
              min={1}
              value={p.meanWindowS}
              onChange={(e) => p.onMeanWindowSChange(parseInt(e.target.value || "1", 10))}
            />
          </label>
        )}

        {p.operation === "quasipeak" && (
          <>
            <label>
              tau_charge_ms&nbsp;
              <input
                type="number"
                min={1}
                value={p.qpChargeMs}
                onChange={(e) => p.onQpParamsChange(parseInt(e.target.value || "1", 10), p.qpDischargeMs)}
              />
            </label>
            <label>
              tau_discharge_ms&nbsp;
              <input
                type="number"
                min={1}
                value={p.qpDischargeMs}
                onChange={(e) => p.onQpParamsChange(p.qpChargeMs, parseInt(e.target.value || "1", 10))}
              />
            </label>
          </>
        )}
      </div>

      <div style={{ marginTop: 10 }}>
        <div style={{ marginBottom: 6 }}>Devices</div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
          {ids.length === 0 && <div style={{ opacity: 0.7 }}>Keine Device_IDs vergeben.</div>}
          {ids.map((id) => (
            <label key={id} style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <input type="checkbox" checked={p.selectedDeviceIds.includes(id)} onChange={() => toggle(id)} />
              {id}
            </label>
          ))}
        </div>
        {p.operation === "sub" && (
          <div style={{ marginTop: 8, opacity: 0.7 }}>
            Subtrahieren nutzt: erstes ausgewähltes Device minus zweites (A - B).
          </div>
        )}
      </div>
    </div>
  );
}