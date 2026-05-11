/**
 * Efficacy chart — AFS before/after an applied intervention.
 *
 * Shows the 13-day baseline window and up to 14 days of post-intervention
 * data.  A vertical ReferenceLine marks the intervention date.
 * A semi-transparent ReferenceArea distinguishes before vs. after phases.
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
import type { EfficacyView, EfficacyPoint } from '../types/interventions';

interface ChartEntry extends EfficacyPoint {
  displayDate: string;
}

function buildEntries(points: EfficacyPoint[]): ChartEntry[] {
  return points.map(p => ({ ...p, displayDate: format(parseISO(p.date), 'MMM d') }));
}

function CustomTooltip({ active, payload, label }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null;
  const pt = payload[0]?.payload as ChartEntry;
  return (
    <div style={{
      backgroundColor: '#fff', border: '1px solid var(--primary-10)',
      borderRadius: 8, padding: '10px 14px', fontFamily: 'var(--fb)', fontSize: 12,
      boxShadow: '0 2px 8px rgba(0,51,102,0.12)',
    }}>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>{label}</div>
      <div style={{ color: pt.phase === 'before' ? 'var(--mid)' : 'var(--primary)', fontWeight: 600, fontSize: 14 }}>
        AFS {pt.afs.toFixed(1)}
      </div>
      <div style={{ color: 'var(--mid)', fontSize: 10, marginTop: 2, textTransform: 'uppercase', letterSpacing: '1px' }}>
        {pt.phase} intervention
      </div>
    </div>
  );
}

interface EfficacyChartProps {
  data: EfficacyView;
  height?: number;
}

export function EfficacyChart({ data, height = 240 }: EfficacyChartProps) {
  const entries = buildEntries(data.points);
  const appliedDate = format(parseISO(data.applied_at), 'MMM d');
  const appliedIdx  = entries.findIndex(e => e.date >= data.applied_at.slice(0, 10));

  const deltaAfs = data.after_avg_afs - data.before_avg_afs;
  const deltaColor = deltaAfs < 0 ? '#27B97C' : deltaAfs > 0 ? '#E03448' : 'var(--mid)';
  const deltaSign  = deltaAfs > 0 ? '+' : '';

  const tickFormatter = (_: string, index: number) =>
    index % 4 === 0 ? entries[index]?.displayDate ?? '' : '';

  return (
    <div>
      {/* Summary stats */}
      <div style={{ display: 'flex', gap: 24, marginBottom: 16 }}>
        {[
          { label: 'Avg AFS before', value: data.before_avg_afs.toFixed(1), color: 'var(--mid)' },
          { label: 'Avg AFS after',  value: data.has_sufficient_data ? data.after_avg_afs.toFixed(1) : '—', color: 'var(--primary)' },
          { label: 'Change',         value: data.has_sufficient_data ? `${deltaSign}${deltaAfs.toFixed(1)}` : '—', color: deltaColor },
        ].map(s => (
          <div key={s.label}>
            <div style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: s.color, lineHeight: 1 }}>{s.value}</div>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 9, color: 'var(--mid)', textTransform: 'uppercase', letterSpacing: '2px', marginTop: 3 }}>{s.label}</div>
          </div>
        ))}
      </div>

      {!data.has_sufficient_data && (
        <p style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', marginBottom: 12, fontStyle: 'italic' }}>
          ≥ 14 days of post-intervention data needed for full efficacy view.
        </p>
      )}

      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={entries} margin={{ top: 8, right: 16, bottom: 0, left: -8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--primary-10)" vertical={false} />

          {/* Zone bands */}
          <ReferenceArea y1={0}  y2={39}  fill="#E0F7EF" fillOpacity={0.4} />
          <ReferenceArea y1={40} y2={69}  fill="#FEF0E6" fillOpacity={0.4} />
          <ReferenceArea y1={70} y2={100} fill="#FDEAEA" fillOpacity={0.4} />

          {/* Before shading */}
          {appliedIdx > 0 && (
            <ReferenceArea
              x1={entries[0]?.displayDate}
              x2={entries[appliedIdx]?.displayDate}
              fill="rgba(107,114,128,0.06)"
            />
          )}

          {/* Intervention marker */}
          <ReferenceLine
            x={appliedDate}
            stroke="var(--gold)"
            strokeWidth={2}
            label={{ value: 'Applied', fill: 'var(--gold)', fontSize: 9, fontFamily: 'var(--fb)' }}
          />

          <XAxis
            dataKey="displayDate"
            tickFormatter={tickFormatter}
            tick={{ fontFamily: 'var(--fb)', fontSize: 11, fill: 'var(--mid)' }}
            axisLine={{ stroke: 'var(--primary-10)' }}
            tickLine={false}
          />
          <YAxis
            domain={[0, 100]}
            ticks={[0, 40, 70, 100]}
            tick={{ fontFamily: 'var(--fb)', fontSize: 11, fill: 'var(--mid)' }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} />

          {/* Before line — muted */}
          <Line
            dataKey={(_: ChartEntry) => _.phase === 'before' ? _.afs : undefined}
            stroke="var(--mid)"
            strokeWidth={1.5}
            strokeDasharray="4 4"
            dot={false}
            name="Before"
            connectNulls={false}
          />
          {/* After line — prominent */}
          <Line
            dataKey={(_: ChartEntry) => _.phase === 'after' ? _.afs : undefined}
            stroke="var(--primary)"
            strokeWidth={2}
            dot={false}
            name="After"
            connectNulls={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
