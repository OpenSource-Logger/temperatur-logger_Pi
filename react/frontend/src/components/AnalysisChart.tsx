import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from "recharts";
import type { NamedSeries } from "../api";

type Props = {
  title: string;
  seriesList: NamedSeries[];
};

export function AnalysisChart({ title, seriesList }: Props) {
  // mergen aller Serien auf gemeinsame "rows" nach Timestamp
  // => Recharts kann dann mehrere Lines aus denselben rows zeichnen
  const map = new Map<number, any>();

  for (const s of seriesList) {
    for (const p of s.series) {
      const tsMs = p.ts * 1000;
      if (!map.has(tsMs)) map.set(tsMs, { ts: tsMs });
      map.get(tsMs)![s.name] = p.value;
    }
  }

  const data = Array.from(map.values()).sort((a, b) => a.ts - b.ts);

  return (
    <div style={{ border: "1px solid #ddd", padding: 12, borderRadius: 8, marginTop: 12 }}>
      <h3 style={{ marginTop: 0 }}>{title}</h3>
      <div style={{ width: "100%", height: 320 }}>
        <ResponsiveContainer>
          <LineChart data={data}>
            <XAxis
              dataKey="ts"
              type="number"
              domain={["dataMin", "dataMax"]}
              tickFormatter={(v) => new Date(v).toLocaleTimeString()}
            />
            <YAxis />
            <Tooltip labelFormatter={(v) => new Date(Number(v)).toLocaleString()} />
            <Legend />
            {seriesList.map((s) => (
              <Line key={s.name} type="monotone" dataKey={s.name} dot={false} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}