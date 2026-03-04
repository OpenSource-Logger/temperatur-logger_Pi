import { useMemo } from "react";
import type { Device } from "../types";

type Props = {
  devices: Device[];
  selectedDeviceIds: string[];
  from: string; // grafana "from" (z.B. "now-6h" oder epoch ms)
  to: string;   // grafana "to" (z.B. "now")
  grafanaBaseUrl: string; // z.B. "http://127.0.0.1:3000"
  dashboardUid: string;   // Grafana Dashboard UID
};

export function GrafanaEmbed(props: Props) {
  const { selectedDeviceIds, from, to, grafanaBaseUrl, dashboardUid } = props;

  const src = useMemo(() => {
    const path = `${grafanaBaseUrl.replace(/\/$/, "")}/d/${dashboardUid}/temperatur-logger`;
    const u = new URL(path, window.location.origin);
    u.searchParams.set("orgId", "1");
    u.searchParams.set("kiosk", "tv"); // reduziert UI
    u.searchParams.set("from", from);
    u.searchParams.set("to", to);

    // multi-select variable: var-device_id mehrfach setzen
    for (const id of selectedDeviceIds) {
      u.searchParams.append("var-device_id", id);
    }

    return u.toString();
  }, [selectedDeviceIds, from, to, grafanaBaseUrl, dashboardUid]);

  return (
    <div style={{ border: "1px solid #ddd", padding: 12, borderRadius: 8, marginTop: 12 }}>
      <h3 style={{ marginTop: 0 }}>Grafana</h3>
      <iframe
        title="grafana"
        src={src}
        style={{ width: "100%", height: 700, border: 0 }}
      />
    </div>
  );
}