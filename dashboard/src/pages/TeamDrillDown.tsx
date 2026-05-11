/**
 * Team drill-down — 30-day AFS trend chart + feature breakdown bars
 * + current zone card + triggered interventions.
 */

import { useParams, useNavigate } from 'react-router-dom';
import { Eyebrow } from '../components/Eyebrow';
import { ZoneBadge } from '../components/ZoneBadge';
import { ResilienceTrendChart } from '../components/ResilienceTrendChart';
import { InterventionPanel } from '../components/InterventionPanel';
import { ChartSkeleton, Skeleton } from '../components/LoadingSkeleton';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { useTeamHistory } from '../hooks/useDashboard';
import { useAuthStore } from '../stores/authStore';
import type { FeatureScores } from '../types/domain';

const FEATURE_CONFIG: Array<{
  key: keyof FeatureScores;
  label: string;
  invert: boolean;  // true = higher is worse
}> = [
  { key: 'calendar_density_score',     label: 'Calendar Density',   invert: true  },
  { key: 'after_hours_activity_index', label: 'After-Hours Index',  invert: true  },
  { key: 'context_switch_count',       label: 'Context Switches',   invert: true  },
  { key: 'sprint_health_index',        label: 'Sprint Health',      invert: false },
];

function FeatureBar({ label, value, invert }: { label: string; value: number; invert: boolean }) {
  const riskLevel = invert ? value : 1 - value;
  const fill = riskLevel > 0.7 ? '#E03448' : riskLevel > 0.4 ? '#F07020' : '#27B97C';
  const pct = Math.round(value * 100);

  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
        <span style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--dark)' }}>{label}</span>
        <span style={{ fontFamily: 'var(--fb)', fontSize: 12, fontWeight: 600, color: 'var(--dark)' }}>{pct}%</span>
      </div>
      <div style={{ height: 8, backgroundColor: 'var(--light)', borderRadius: 4, overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${pct}%`, backgroundColor: fill, borderRadius: 4, transition: 'width 0.4s ease' }} />
      </div>
    </div>
  );
}


export function TeamDrillDown() {
  const { teamId } = useParams<{ teamId: string }>();
  const navigate   = useNavigate();
  const { user }   = useAuthStore();
  const query      = useTeamHistory(teamId ?? '');

  // RBAC: team_manager can only view their own team
  if (user?.role === 'team_manager' && user.team_id && teamId !== user.team_id) {
    return (
      <main style={{ maxWidth: 1300, margin: '0 auto', padding: '80px 48px', textAlign: 'center' }}>
        <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: '#E03448' }}>
          Access denied — you can only view your own team's data.
        </p>
        <button
          onClick={() => navigate(`/team/${user.team_id}`)}
          style={{ marginTop: 16, background: 'none', border: 'none', color: 'var(--primary)', cursor: 'pointer', fontFamily: 'var(--fb)', fontSize: 13, textDecoration: 'underline' }}
        >
          Go to your team →
        </button>
      </main>
    );
  }

  return (
    <main style={{ maxWidth: 1300, margin: '0 auto', padding: '40px 48px' }}>
      {/* Back link */}
      {user?.role !== 'team_manager' && (
        <button
          onClick={() => navigate('/dashboard')}
          aria-label="Back to dashboard"
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--mid)',
            cursor: 'pointer',
            fontFamily: 'var(--fb)',
            fontSize: 12,
            marginBottom: 24,
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: 0,
          }}
        >
          ← Back to Dashboard
        </button>
      )}

      {query.isLoading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          <Skeleton height={28} width="40%" />
          <Skeleton height={14} width="25%" />
          <ChartSkeleton height={280} />
        </div>
      ) : query.isError ? (
        <div role="alert" style={{ color: '#E03448', fontFamily: 'var(--fb)', fontSize: 13 }}>
          Team not found. <button onClick={() => navigate('/dashboard')} style={{ background: 'none', border: 'none', color: 'var(--primary)', cursor: 'pointer', textDecoration: 'underline' }}>Return to dashboard.</button>
        </div>
      ) : query.data ? (() => {
        const { data } = query;
        return (
          <>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12, marginBottom: 32 }}>
              <div>
                <Eyebrow>{data.department}</Eyebrow>
                <h1 style={{ fontFamily: 'var(--fd)', fontSize: 28, fontWeight: 300, color: 'var(--dark)', margin: '0 0 8px' }}>
                  {data.team_name}
                </h1>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <ZoneBadge zone={data.zone} size="md" />
                  <span style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)' }}>
                    AFS {data.afs.toFixed(1)}
                  </span>
                </div>
              </div>
            </div>

            {/* Two-column layout */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 24, alignItems: 'start' }}>

              {/* Left — trend chart */}
              <ErrorBoundary>
                <div style={{ backgroundColor: '#fff', borderRadius: 12, padding: '24px 20px', boxShadow: '0 1px 4px rgba(0,51,102,0.08)' }}>
                  <Eyebrow>30-day trend</Eyebrow>
                  <h2 style={{ fontFamily: 'var(--fd)', fontSize: 17, fontWeight: 300, color: 'var(--dark)', margin: '0 0 20px' }}>
                    Attention Fragmentation Score
                  </h2>
                  <div style={{ display: 'flex', gap: 24, marginBottom: 12 }}>
                    {[
                      { color: '#E0F7EF', label: 'Healthy  0–39'  },
                      { color: '#FEF0E6', label: 'Monitor 40–69'  },
                      { color: '#FDEAEA', label: 'Intervene 70+'  },
                    ].map(l => (
                      <div key={l.label} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <div style={{ width: 12, height: 12, borderRadius: 3, backgroundColor: l.color, border: '1px solid rgba(0,0,0,0.1)' }} />
                        <span style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)' }}>{l.label}</span>
                      </div>
                    ))}
                  </div>
                  <ResilienceTrendChart history={data.history} height={260} />
                </div>
              </ErrorBoundary>

              {/* Right — feature breakdown + interventions */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                {/* Feature breakdown */}
                <div style={{ backgroundColor: '#fff', borderRadius: 12, padding: '20px', boxShadow: '0 1px 4px rgba(0,51,102,0.08)' }}>
                  <Eyebrow>Feature breakdown</Eyebrow>
                  {FEATURE_CONFIG.map(fc => (
                    <FeatureBar
                      key={fc.key}
                      label={fc.label}
                      value={data.features[fc.key]}
                      invert={fc.invert}
                    />
                  ))}
                </div>

                {/* Interventions */}
                <div>
                  <Eyebrow>Interventions</Eyebrow>
                  <InterventionPanel
                    teamId={data.team_id}
                    suggestedInterventions={data.interventions}
                  />
                </div>
              </div>
            </div>
          </>
        );
      })() : null}
    </main>
  );
}
