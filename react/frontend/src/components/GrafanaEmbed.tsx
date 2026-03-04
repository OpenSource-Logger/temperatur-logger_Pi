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
    const baseUrl = grafanaBaseUrl.replace(/\/$/, "");
    const path = `${baseUrl}/d/${dashboardUid}/temperatur-logger`;
    
    const params = new URLSearchParams();
    params.set("orgId", "1");
    params.set("kiosk", "tv");
    params.set("from", from);
    params.set("to", to);
    
    for (const id of selectedDeviceIds) {
      params.append("var-device_id", id);
    }
    
    return `${path}?${params.toString()}`;
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