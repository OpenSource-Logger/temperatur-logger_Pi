import { useMemo } from "react";
import type { Device } from "../types";

type Props = {
  devices: Device[];
  selected: string[];
  onSelectedChange: (next: string[]) => void;

  from: string;
  to: string;
  onFromToChange: (from: string, to: string) => void;
};

const PRESETS = [
  { label: "1h", from: "now-1h", to: "now" },
  { label: "6h", from: "now-6h", to: "now" },
  { label: "24h", from: "now-24h", to: "now" },
  { label: "7d", from: "now-7d", to: "now" },
];

export function PlotControls(props: Props) {
  const { devices, selected, onSelectedChange, from, to, onFromToChange } = props;

  const deviceIds = useMemo(
    () => devices.map((d) => d.device_id).filter((x): x is string => !!x),
    [devices]
  );

  function toggle(id: string) {
    if (selected.includes(id)) onSelectedChange(selected.filter((x) => x !== id));
    else onSelectedChange([...selected, id]);
  }

  return (
    <div style={{ border: "1px solid #ddd", padding: 12, borderRadius: 8, marginTop: 12 }}>
      <h3 style={{ marginTop: 0 }}>Plot-Auswahl</h3>

      <div style={{ marginBottom: 8 }}>
        Zeitraum:&nbsp;
        {PRESETS.map((p) => (
          <button
            key={p.label}
            onClick={() => onFromToChange(p.from, p.to)}
            style={{ marginRight: 8 }}
          >
            {p.label}
          </button>
        ))}
        <span style={{ marginLeft: 8, opacity: 0.7 }}>
          aktuell: from={from}, to={to}
        </span>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
        {deviceIds.length === 0 && <div style={{ opacity: 0.7 }}>Keine Device_IDs vergeben.</div>}
        {deviceIds.map((id) => (
          <label key={id} style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <input
              type="checkbox"
              checked={selected.includes(id)}
              onChange={() => toggle(id)}
            />
            {id}
          </label>
        ))}
      </div>
    </div>
  );
}