/**
 * Multi-series AFS trend chart — org, department, and team lines overlaid.
 * Zone reference bands (green/yellow/red) provide threshold context.
 */

import {
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceArea,
  ReferenceLine,
  Legend,
  ResponsiveContainer,
  type TooltipProps,
} from 'recharts';
import { format, parseISO } from 'date-fns';
import type { OrgTrendPoint } from '../types/domain';

interface TrendEntry {
  date: string;
  displayDate: string;
  org?: number;
  dept?: number;
  team?: number;
}

function buildEntries(
  org: OrgTrendPoint[],
  dept?: OrgTrendPoint[],
  team?: OrgTrendPoint[],
): TrendEntry[] {
  const byDate: Record<string, TrendEntry> = {};
  for (const pt of org) {
    byDate[pt.date] = {
      date: pt.date,
      displayDate: format(parseISO(pt.date), 'MMM d'),
      org: pt.afs,
    };
  }
  for (const pt of dept ?? []) {
    const entry = byDate[pt.date];
    if (entry) entry.dept = pt.afs;
  }
  for (const pt of team ?? []) {
    const entry = byDate[pt.date];
    if (entry) entry.team = pt.afs;
  }
  return Object.values(byDate).sort((a, b) => a.date.localeCompare(b.date));
}

function ChartTooltip({ active, payload, label }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null;
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
      <div style={{ fontWeight: 600, color: 'var(--dark)', marginBottom: 6 }}>{label}</div>
      {payload.map(p => (
        <div key={p.name} style={{ color: p.stroke ?? '#333', marginBottom: 2 }}>
          {p.name}:{' '}
          <strong>{typeof p.value === 'number' ? p.value.toFixed(1) : p.value}</strong>
        </div>
      ))}
    </div>
  );
}

interface AfsTrendChartProps {
  orgHistory: OrgTrendPoint[];
  deptHistory?: OrgTrendPoint[];
  teamHistory?: OrgTrendPoint[];
  deptLabel?: string;
  teamLabel?: string;
  height?: number;
}

export function AfsTrendChart({
  orgHistory,
  deptHistory,
  teamHistory,
  deptLabel = 'Department',
  teamLabel = 'Team',
  height = 300,
}: AfsTrendChartProps) {
  const entries = buildEntries(orgHistory, deptHistory, teamHistory);
  const tickFormatter = (_: string, index: number) =>
    index % Math.ceil(entries.length / 6) === 0
      ? (entries[index]?.displayDate ?? '')
      : '';

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={entries} margin={{ top: 8, right: 16, bottom: 0, left: -8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--primary-10)" vertical={false} />

        <ReferenceArea y1={0}  y2={39}  fill="#E0F7EF" fillOpacity={0.4} />
        <ReferenceArea y1={40} y2={69}  fill="#FEF0E6" fillOpacity={0.4} />
        <ReferenceArea y1={70} y2={100} fill="#FDEAEA" fillOpacity={0.4} />
        <ReferenceLine y={40} stroke="#F07020" strokeDasharray="4 4" strokeWidth={1.5} />
        <ReferenceLine y={70} stroke="#E03448" strokeDasharray="4 4" strokeWidth={1.5} />

        <XAxis
          dataKey="displayDate"
          tickFormatter={tickFormatter}
          tick={{ fontFamily: 'var(--fb)', fontSize: 11, fill: 'var(--mid)' }}
          axisLine={{ stroke: 'var(--primary-10)' }}
          tickLine={false}
        />
        <YAxis
          domain={[0, 100]}
          ticks={[0, 20, 40, 60, 70, 80, 100]}
          tick={{ fontFamily: 'var(--fb)', fontSize: 11, fill: 'var(--mid)' }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip content={<ChartTooltip />} />
        <Legend
          wrapperStyle={{ fontFamily: 'var(--fb)', fontSize: 11, paddingTop: 8 }}
        />

        <Line
          dataKey="org"
          stroke="#003366"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4, stroke: '#003366', strokeWidth: 2, fill: '#fff' }}
          name="All Company"
          connectNulls
        />
        {deptHistory && (
          <Line
            dataKey="dept"
            stroke="#C8982A"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, stroke: '#C8982A', strokeWidth: 2, fill: '#fff' }}
            name={deptLabel}
            connectNulls
          />
        )}
        {teamHistory && (
          <Line
            dataKey="team"
            stroke="#F07020"
            strokeWidth={2}
            strokeDasharray="6 3"
            dot={false}
            activeDot={{ r: 4, stroke: '#F07020', strokeWidth: 2, fill: '#fff' }}
            name={teamLabel}
            connectNulls
          />
        )}
      </ComposedChart>
    </ResponsiveContainer>
  );
}
