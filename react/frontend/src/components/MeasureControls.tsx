import { useState } from "react";
import { measurePause, measureStart, measureStop } from "../api";

export function MeasureControls() {
  const [intervalS, setIntervalS] = useState(5);
  const [mode, setMode] = useState<"count" | "duration">("duration");
  const [value, setValue] = useState(60); // duration_s oder count
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onStart() {
    setBusy(true);
    setError(null);
    try {
      await measureStart(intervalS, mode, value);
    } catch (e: any) {
      setError(e.message ?? String(e));
    } finally {
      setBusy(false);
    }
  }

  async function onPause() {
    setBusy(true);
    setError(null);
    try {
      await measurePause();
    } catch (e: any) {
      setError(e.message ?? String(e));
    } finally {
      setBusy(false);
    }
  }

  async function onStop() {
    setBusy(true);
    setError(null);
    try {
      await measureStop();
    } catch (e: any) {
      setError(e.message ?? String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ border: "1px solid #ddd", padding: 12, borderRadius: 8, marginBottom: 12 }}>
      <h3 style={{ marginTop: 0 }}>Messreihe (global)</h3>

      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
        <label>
          Intervall (s)&nbsp;
          <input
            type="number"
            min={1}
            value={intervalS}
            onChange={(e) => setIntervalS(parseInt(e.target.value || "1", 10))}
          />
        </label>

        <label>
          Modus&nbsp;
          <select value={mode} onChange={(e) => setMode(e.target.value as any)}>
            <option value="duration">Dauer (s)</option>
            <option value="count">Anzahl</option>
          </select>
        </label>

        <label>
          Wert&nbsp;
          <input
            type="number"
            min={1}
            value={value}
            onChange={(e) => setValue(parseInt(e.target.value || "1", 10))}
          />
        </label>

        <button onClick={onStart} disabled={busy}>Start</button>
        <button onClick={onPause} disabled={busy}>Pause</button>
        <button onClick={onStop} disabled={busy}>Stop</button>
      </div>

      {error && <div style={{ color: "crimson", marginTop: 8 }}>{error}</div>}
    </div>
  );
}