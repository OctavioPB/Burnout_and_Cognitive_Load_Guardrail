/**
 * Department heatmap — grid of team cards grouped by department,
 * color-coded by resilience zone.  Clicking a card navigates to
 * the team's drill-down page.
 */

import { useNavigate } from 'react-router-dom';
import type { TeamCard } from '../types/domain';
import { ZoneBadge } from './ZoneBadge';

import type { ResilienceZone } from '../types/domain';

const ZONE_BORDER: Record<ResilienceZone, string> = {
  green:  '#27B97C',
  yellow: '#F07020',
  red:    '#E03448',
};

function Sparkline({ values, color }: { values: number[]; color: string }) {
  const W = 100;
  const H = 28;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = Math.max(max - min, 5); // minimum span so stable teams still show a line
  const pts = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * W;
      const y = H - ((v - min) / range) * H;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
  return (
    <svg
      width="100%"
      height={H}
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="none"
      style={{ display: 'block' }}
      aria-hidden="true"
    >
      <polyline
        points={pts}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}

function TeamCardItem({ card, sparkline }: { card: TeamCard; sparkline?: number[] }) {
  const navigate = useNavigate();

  return (
    <button
      onClick={() => navigate(`/team/${card.team_id}`)}
      aria-label={`${card.team_name} — AFS ${card.afs.toFixed(1)}, ${card.zone} zone`}
      style={{
        background: '#fff',
        border: `1px solid ${ZONE_BORDER[card.zone]}22`,
        borderTop: `3px solid ${ZONE_BORDER[card.zone]}`,
        borderRadius: 10,
        padding: '16px 18px',
        cursor: 'pointer',
        textAlign: 'left',
        width: '100%',
        transition: 'box-shadow 0.15s, transform 0.1s',
        boxShadow: '0 1px 4px rgba(0,51,102,0.06)',
      }}
      onMouseEnter={e => {
        (e.currentTarget as HTMLElement).style.boxShadow = '0 4px 12px rgba(0,51,102,0.14)';
        (e.currentTarget as HTMLElement).style.transform = 'translateY(-1px)';
      }}
      onMouseLeave={e => {
        (e.currentTarget as HTMLElement).style.boxShadow = '0 1px 4px rgba(0,51,102,0.06)';
        (e.currentTarget as HTMLElement).style.transform = 'translateY(0)';
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8, marginBottom: 10 }}>
        <span style={{ fontFamily: 'var(--fb)', fontSize: 13, fontWeight: 600, color: 'var(--dark)', lineHeight: 1.3 }}>
          {card.team_name}
        </span>
        {card.has_active_alert && (
          <span
            aria-label="Active alert"
            title="Active alert"
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              backgroundColor: '#E03448',
              flexShrink: 0,
              marginTop: 3,
            }}
          />
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <div style={{ fontFamily: 'var(--fd)', fontSize: 24, fontWeight: 300, color: 'var(--dark)', lineHeight: 1 }}>
            {card.afs.toFixed(1)}
          </div>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 9, color: 'var(--mid)', letterSpacing: '1px', textTransform: 'uppercase', marginTop: 2 }}>
            AFS
          </div>
        </div>
        <ZoneBadge zone={card.zone} />
      </div>

      {sparkline && sparkline.length >= 2 && (
        <div style={{ marginTop: 10 }}>
          <Sparkline values={sparkline} color={ZONE_BORDER[card.zone]} />
          <div style={{ fontFamily: 'var(--fb)', fontSize: 9, color: 'var(--mid)', letterSpacing: '1px', textTransform: 'uppercase', marginTop: 2 }}>
            7-day trend
          </div>
        </div>
      )}
    </button>
  );
}

interface DepartmentHeatmapProps {
  teams: TeamCard[];
  sparklines?: Record<string, number[]>;
}

export function DepartmentHeatmap({ teams, sparklines }: DepartmentHeatmapProps) {
  // Group by department
  const byDept = teams.reduce<Record<string, TeamCard[]>>((acc, card) => {
    (acc[card.department] ??= []).push(card);
    return acc;
  }, {});

  const departments = Object.keys(byDept).sort();

  if (departments.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--mid)', fontFamily: 'var(--fb)', fontSize: 14 }}>
        No team data available.
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 36 }}>
      {departments.map(dept => (
        <section key={dept} aria-label={`${dept} department`}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
            <span
              style={{
                fontFamily: 'var(--fb)',
                fontSize: 9,
                fontWeight: 700,
                letterSpacing: '3px',
                textTransform: 'uppercase',
                color: 'var(--primary)',
                backgroundColor: 'var(--primary-10)',
                padding: '4px 10px',
                borderRadius: 6,
              }}
            >
              {dept}
            </span>
            <span style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>
              {byDept[dept]?.length ?? 0} {(byDept[dept]?.length ?? 0) === 1 ? 'team' : 'teams'}
            </span>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
              gap: 12,
            }}
          >
            {(byDept[dept] ?? []).map(card => {
              const sl = sparklines?.[card.team_id];
              return (
                <TeamCardItem
                  key={card.team_id}
                  card={card}
                  {...(sl !== undefined ? { sparkline: sl } : {})}
                />
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
