import type { Device } from "./types";

const BASE_URL = "http://127.0.0.1:8000";

async function req<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return (await res.json()) as T;
}

export async function listDevices(): Promise<Device[]> {
  return req<Device[]>("/devices");
}

export async function assignDeviceId(chipId: string, deviceId: string): Promise<{ ok: boolean }> {
  return req(`/devices/${encodeURIComponent(chipId)}/assign`, {
    method: "POST",
    body: JSON.stringify({ device_id: deviceId }),
  });
}

export async function setSensorType(deviceId: string, sensorType: string, sensorParams?: string | null) {
  return req(`/devices/${encodeURIComponent(deviceId)}/sensor`, {
    method: "POST",
    body: JSON.stringify({ sensor_type: sensorType, sensor_params: sensorParams ?? null }),
  });
}

export async function blink(deviceId: string, durationMs = 2000, periodMs = 200) {
  return req(`/devices/${encodeURIComponent(deviceId)}/blink`, {
    method: "POST",
    body: JSON.stringify({ duration_ms: durationMs, period_ms: periodMs }),
  });
}

export async function measureStart(intervalS: number, mode: "count" | "duration", value: number) {
  const payload: any = { interval_s: intervalS };
  if (mode === "count") payload.count = value;
  else payload.duration_s = value;

  return req("/measure/start", { method: "POST", body: JSON.stringify(payload) });
}

export async function measurePause() {
  return req("/measure/pause", { method: "POST" });
}

export async function measureStop() {
  return req("/measure/stop", { method: "POST" });
}

export type AnalysisOperation = "raw" | "mean" | "add" | "sub" | "peak" | "quasipeak";

export type AnalysisRequest = {
  device_ids: string[];
  from: string; // frei: "now-6h" oder ISO oder epoch-ms-string
  to: string;
  operation: AnalysisOperation;
  params?: Record<string, any>;
  downsample_s?: number | null;
};

export type Point = { ts: number; value: number };

export type NamedSeries = {
  name: string;
  series: Point[];
};

export type AnalysisResponse = {
  series_list: NamedSeries[];
  scalar?: number | null;
};

export async function analysisSeries(reqBody: AnalysisRequest): Promise<AnalysisResponse> {
  return req<AnalysisResponse>("/analysis/series", {
    method: "POST",
    body: JSON.stringify(reqBody),
  });
}