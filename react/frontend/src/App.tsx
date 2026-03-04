import { useEffect, useState } from "react";
import type { Device } from "./types";
import { listDevices } from "./api";
import { DeviceTable } from "./components/DeviceTable";
import { MeasureControls } from "./components/MeasureControls";
import { PlotControls } from "./components/PlotControls";
import { GrafanaEmbed } from "./components/GrafanaEmbed";
import { AnalysisControls } from "./components/AnalysisControls";
import { AnalysisChart } from "./components/AnalysisChart";
import { analysisSeries } from "./api";
import type { AnalysisOperation } from "./api";
import type { NamedSeries } from "./api";

export default function App() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [selectedDeviceIds, setSelectedDeviceIds] = useState<string[]>([]);
  const [from, setFrom] = useState("now-6h");
  const [to, setTo] = useState("now");

  const [operation, setOperation] = useState<AnalysisOperation>("mean");
  const [meanWindowS, setMeanWindowS] = useState(10);
  const [qpChargeMs, setQpChargeMs] = useState(500);
  const [qpDischargeMs, setQpDischargeMs] = useState(1500);

  const [analysisSeriesList, setAnalysisSeriesList] = useState<NamedSeries[] | null>(null);
  const [analysisScalar, setAnalysisScalar] = useState<number | null>(null);
  const [analysisBusy, setAnalysisBusy] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  async function runAnalysis() {
    setAnalysisBusy(true);
    setAnalysisError(null);
    try {
      const params: Record<string, any> = {};
      if (operation === "mean") params.window_s = meanWindowS;
      if (operation === "quasipeak") {
        params.tau_charge_ms = qpChargeMs;
        params.tau_discharge_ms = qpDischargeMs;
      }

      const res = await analysisSeries({
        device_ids: selectedDeviceIds,
        from,
        to,
        operation,
        params,
        downsample_s: 1, // 1s Buckets; später UI-Option
      });

      setAnalysisSeriesList(res.series_list);
      setAnalysisScalar(res.scalar ?? null);
    } catch (e: any) {
      setAnalysisError(e.message ?? String(e));
    } finally {
      setAnalysisBusy(false);
    }
  }

  async function refresh() {
    setError(null);
    try {
      const d = await listDevices();
      setDevices(d);

      // Auto-select: wenn noch nichts gewählt ist, wähle alle vorhandenen device_ids
      if (selectedDeviceIds.length === 0) {
        const ids = d.map((x) => x.device_id).filter((x): x is string => !!x);
        setSelectedDeviceIds(ids);
      } else {
        // entferne selections, die nicht mehr existieren
        const existing = new Set(d.map((x) => x.device_id).filter((x): x is string => !!x));
        setSelectedDeviceIds((prev) => prev.filter((id) => existing.has(id)));
      }
    } catch (e: any) {
      setError(e.message ?? String(e));
    }
  }

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 2000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: 16, fontFamily: "sans-serif" }}>
      <h2>Temperatur-Logger</h2>

      <MeasureControls />

      {error && <div style={{ color: "crimson", marginBottom: 12 }}>{error}</div>}

      <DeviceTable devices={devices} onRefresh={refresh} />

      <PlotControls
        devices={devices}
        selected={selectedDeviceIds}
        onSelectedChange={setSelectedDeviceIds}
        from={from}
        to={to}
        onFromToChange={(f, t) => {
          setFrom(f);
          setTo(t);
        }}
      />

      <AnalysisControls
        devices={devices}
        selectedDeviceIds={selectedDeviceIds}
        onSelectedDeviceIdsChange={setSelectedDeviceIds}
        from={from}
        to={to}
        onFromToChange={(f, t) => { setFrom(f); setTo(t); }}
        operation={operation}
        onOperationChange={setOperation}
        meanWindowS={meanWindowS}
        onMeanWindowSChange={setMeanWindowS}
        qpChargeMs={qpChargeMs}
        qpDischargeMs={qpDischargeMs}
        onQpParamsChange={(c, d) => { setQpChargeMs(c); setQpDischargeMs(d); }}
      />

      <div style={{ marginTop: 8 }}>
        <button onClick={runAnalysis} disabled={analysisBusy || selectedDeviceIds.length === 0}>
          Analyse ausführen
        </button>
        {analysisScalar !== null && (
          <span style={{ marginLeft: 12, opacity: 0.8 }}>
            Ergebnis: {analysisScalar.toFixed(3)}
          </span>
        )}
        {analysisError && <div style={{ color: "crimson", marginTop: 8 }}>{analysisError}</div>}
      </div>

{analysisSeriesList && analysisSeriesList.length > 0 && (
  <AnalysisChart title={`Analyse: ${operation}`} seriesList={analysisSeriesList} />
)}

      <GrafanaEmbed
        devices={devices}
        selectedDeviceIds={selectedDeviceIds}
        from={from}
        to={to}
        grafanaBaseUrl="192.168.0.98/grafana/"
        dashboardUid="adn5fwm"
      />
    </div>
  );
}