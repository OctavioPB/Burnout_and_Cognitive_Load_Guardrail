/**
 * Horizontal bar chart — AFS by department or by team.
 * Bars are zone-colored; reference lines mark the 40 and 70 thresholds.
 */

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  LabelList,
  ResponsiveContainer,
  Cell,
  type TooltipProps,
} from 'recharts';

export interface BarEntry {
  name: string;
  afs: number;
}

const ZONE_COLOR: Record<string, string> = {
  green:  '#0C2B4E',
  yellow: '#385A87',
  red:    '#E03448',
};

function zoneOf(afs: number): string {
  if (afs < 40) return 'green';
  if (afs < 70) return 'yellow';
  return 'red';
}

function ChartTooltip({ active, payload }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload as BarEntry;
  const zone = zoneOf(d.afs);
  return (
    <div
      style={{
        backgroundColor: '#fff',
        border: '1px solid var(--primary-10)',
        borderRadius: 8,
        padding: '10px 14px',
        fontFamily: 'var(--fb)',
        fontSize: 12,
        boxShadow: '0 2px 8px rgba(0,51,102,0.12)',
      }}
    >
      <div style={{ fontWeight: 600, color: 'var(--dark)', marginBottom: 4 }}>{d.name}</div>
      <div style={{ color: ZONE_COLOR[zone], fontWeight: 600, fontSize: 14 }}>
        AFS {d.afs.toFixed(1)}
      </div>
    </div>
  );
}

interface AfsBarChartProps {
  entries: BarEntry[];
  yAxisWidth?: number;
  height?: number;
}

export function AfsBarChart({ entries, yAxisWidth = 130, height = 260 }: AfsBarChartProps) {
  return (
    <ResponsiveContainer width="100%" height={Math.max(height, entries.length * 36 + 40)}>
      <BarChart
        layout="vertical"
        data={entries}
        margin={{ top: 4, right: 48, bottom: 4, left: 0 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="var(--primary-10)" horizontal={false} />

        <XAxis
          type="number"
          domain={[0, 100]}
          ticks={[0, 20, 40, 60, 70, 80, 100]}
          tick={{ fontFamily: 'var(--fb)', fontSize: 11, fill: 'var(--mid)' }}
          axisLine={{ stroke: 'var(--primary-10)' }}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="name"
          width={yAxisWidth}
          tick={{ fontFamily: 'var(--fb)', fontSize: 12, fill: 'var(--dark)' }}
          axisLine={false}
          tickLine={false}
        />

        <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(0,51,102,0.04)' }} />

        <ReferenceLine x={40} stroke="#F07020" strokeDasharray="4 4" strokeWidth={1.5} />
        <ReferenceLine x={70} stroke="#E03448" strokeDasharray="4 4" strokeWidth={1.5} />

        <Bar dataKey="afs" radius={[0, 4, 4, 0]} maxBarSize={28}>
          {entries.map((entry, i) => (
            <Cell key={i} fill={ZONE_COLOR[zoneOf(entry.afs)]} fillOpacity={0.85} />
          ))}
          <LabelList
            dataKey="afs"
            position="right"
            formatter={(v: number) => v.toFixed(1)}
            style={{ fontFamily: 'var(--fb)', fontSize: 11, fill: 'var(--mid)' }}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
