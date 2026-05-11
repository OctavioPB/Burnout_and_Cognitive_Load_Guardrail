/**
 * 30-day AFS trend chart with resilience zone bands.
 *
 * Uses Recharts ComposedChart with:
 * - ReferenceArea for each zone band (green 0-39, yellow 40-69, red 70-100)
 * - ReferenceLine at zone thresholds (40 and 70)
 * - Line for AFS values
 */

import {
  ComposedChart,
  Line,
  ReferenceArea,
  ReferenceLine,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  type TooltipProps,
} from 'recharts';
import { format, parseISO } from 'date-fns';
import type { DayPoint } from '../types/domain';

interface ChartEntry extends DayPoint {
  displayDate: string;
}

function buildEntries(history: DayPoint[]): ChartEntry[] {
  return history.map(pt => ({
    ...pt,
    displayDate: format(parseISO(pt.date), 'MMM d'),
  }));
}

function CustomTooltip({ active, payload, label }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null;
  const pt = payload[0]?.payload as ChartEntry;
  return (
    <div
      style={{
        backgroundColor: '#fff',
        border: '1px solid var(--primary-10)',
        borderRadius: 8,
        padding: '10px 14px',
        boxShadow: '0 2px 8px rgba(0,51,102,0.12)',
        fontFamily: 'var(--fb)',
        fontSize: 12,
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: 6 }}>{label}</div>
      <div style={{ color: 'var(--primary)', fontWeight: 600, fontSize: 14, marginBottom: 4 }}>
        AFS {pt.afs.toFixed(1)}
      </div>
      <div style={{ color: 'var(--mid)', fontSize: 11, lineHeight: 1.7 }}>
        <div>Calendar density: {(pt.calendar_density_score * 100).toFixed(0)}%</div>
        <div>After-hours: {(pt.after_hours_activity_index * 100).toFixed(0)}%</div>
        <div>Context switches: {(pt.context_switch_count * 100).toFixed(0)}%</div>
        <div>Sprint health: {(pt.sprint_health_index * 100).toFixed(0)}%</div>
      </div>
    </div>
  );
}

interface ResilienceTrendChartProps {
  history: DayPoint[];
  height?: number;
}

export function ResilienceTrendChart({ history, height = 280 }: ResilienceTrendChartProps) {
  const entries = buildEntries(history);
  // Show every 5th label on x-axis to avoid crowding
  const tickFormatter = (_: string, index: number) =>
    index % 5 === 0 ? entries[index]?.displayDate ?? '' : '';

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={entries} margin={{ top: 8, right: 16, bottom: 0, left: -8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--primary-10)" vertical={false} />

        {/* Zone bands */}
        <ReferenceArea y1={0}  y2={39}  fill="#E0F7EF" fillOpacity={0.5} ifOverflow="visible" />
        <ReferenceArea y1={40} y2={69}  fill="#FEF0E6" fillOpacity={0.5} ifOverflow="visible" />
        <ReferenceArea y1={70} y2={100} fill="#FDEAEA" fillOpacity={0.5} ifOverflow="visible" />

        {/* Zone threshold lines */}
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
          tickFormatter={v => String(v)}
        />
        <Tooltip content={<CustomTooltip />} />

        <Line
          dataKey="afs"
          stroke="var(--primary)"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4, stroke: 'var(--primary)', strokeWidth: 2, fill: '#fff' }}
          name="AFS"
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
