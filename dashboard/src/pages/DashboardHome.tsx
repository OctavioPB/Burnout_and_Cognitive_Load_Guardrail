/**
 * Dashboard Home — org-wide KPI summary, AFS bar chart, 30-day trend, and team heatmap.
 *
 * Layout:
 *  1. Dark hero section — title only (no stat row)
 *  2. Slicer bar — period, department, team
 *  3. KPI row — zone counts
 *  4. AFS bar chart — by department or by team (toggle)
 *  5. 30-day AFS trend — org / dept / team lines
 *  6. Department heatmap with 7-day sparklines
 */

import { useState } from 'react';
import { Eyebrow } from '../components/Eyebrow';
import { KpiCard } from '../components/KpiCard';
import { AfsBarChart } from '../components/AfsBarChart';
import { AfsTrendChart } from '../components/AfsTrendChart';
import { DepartmentHeatmap } from '../components/DepartmentHeatmap';
import { CardSkeleton } from '../components/LoadingSkeleton';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { useDashboardSummary, useTeams, useOrgHistory } from '../hooks/useDashboard';

// ── Pill button shared style helpers ─────────────────────────────────────────

function pillStyle(active: boolean) {
  return {
    background: active ? 'var(--primary)' : '#fff',
    color: active ? '#fff' : 'var(--primary)',
    border: `1px solid ${active ? 'var(--primary)' : 'var(--primary-10)'}`,
    borderRadius: 20,
    padding: '4px 14px',
    fontFamily: 'var(--fb)',
    fontSize: 11,
    fontWeight: 500,
    cursor: 'pointer' as const,
    transition: 'all 0.15s',
    letterSpacing: '0.5px',
  };
}

const SLICER_LABEL: React.CSSProperties = {
  fontFamily: 'var(--fb)',
  fontSize: 9,
  fontWeight: 700,
  letterSpacing: '2px',
  textTransform: 'uppercase',
  color: 'var(--mid)',
  flexShrink: 0,
};

// ── Section wrapper ───────────────────────────────────────────────────────────

function Section({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        maxWidth: 1300,
        margin: '0 auto',
        padding: '40px 48px',
        borderBottom: '1px solid var(--primary-10)',
      }}
    >
      {children}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function DashboardHome() {
  const [dateRange, setDateRange] = useState<7 | 14 | 30>(30);
  const [selectedDept, setSelectedDept] = useState<string | undefined>();
  const [selectedTeam, setSelectedTeam] = useState<string | undefined>();
  const [scope, setScope] = useState<'company' | 'department' | 'team'>('company');

  const summaryQuery = useDashboardSummary();
  const teamsQuery   = useTeams();
  const orgHistQuery = useOrgHistory();

  const allTeams    = teamsQuery.data ?? [];
  const departments = (summaryQuery.data?.departments ?? []).map(d => d.department).sort();

  const handleDeptChange = (dept: string | undefined) => {
    setSelectedDept(dept);
    setSelectedTeam(undefined);
  };

  const handleScopeChange = (newScope: 'company' | 'department' | 'team') => {
    setScope(newScope);
  };

  // ── Derived data ──────────────────────────────────────────────────────────

  const deptBarEntries = departments.map(dept => {
    const deptTeams = allTeams.filter(t => t.department === dept);
    const avg = deptTeams.length
      ? deptTeams.reduce((s, t) => s + t.afs, 0) / deptTeams.length
      : 0;
    return { name: dept, afs: parseFloat(avg.toFixed(1)) };
  });

  const teamBarEntries = (selectedDept
    ? allTeams.filter(t => t.department === selectedDept)
    : allTeams
  ).map(t => ({ name: t.team_name, afs: t.afs }));

  const barEntries = scope === 'company' ? deptBarEntries : teamBarEntries;

  const orgTrend  = orgHistQuery.data?.org.slice(-dateRange) ?? [];
  const deptTrend = scope !== 'company' && selectedDept
    ? orgHistQuery.data?.by_department[selectedDept]?.slice(-dateRange)
    : undefined;
  const teamTrend = scope === 'team' && selectedTeam
    ? orgHistQuery.data?.by_team[selectedTeam]?.history.slice(-dateRange)
    : undefined;
  const teamLabel = scope === 'team' && selectedTeam
    ? orgHistQuery.data?.by_team[selectedTeam]?.name
    : undefined;

  // Sparklines — last 7 days per team
  const sparklines: Record<string, number[]> = {};
  if (orgHistQuery.data) {
    for (const [tid, series] of Object.entries(orgHistQuery.data.by_team)) {
      sparklines[tid] = series.history.slice(-7).map(p => p.afs);
    }
  }

  // Heatmap teams (filtered by selected dept)
  const heatmapTeams = selectedDept
    ? allTeams.filter(t => t.department === selectedDept)
    : allTeams;

  // Team dropdown options (filtered by selected dept)
  const teamOptions = selectedDept
    ? allTeams.filter(t => t.department === selectedDept)
    : allTeams;

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <main>
      {/* Hero — title only */}
      <section
        className="hero-dark"
        aria-labelledby="hero-title"
        style={{ padding: '48px 48px 40px' }}
      >
        <div style={{ maxWidth: 1300, margin: '0 auto' }}>
          <h1
            id="hero-title"
            style={{
              fontFamily: 'var(--fd)',
              fontSize: 32,
              fontWeight: 300,
              color: '#fff',
              margin: '0 0 10px',
              lineHeight: 1.25,
            }}
          >
            Org-wide resilience,{' '}
            <em style={{ fontStyle: 'italic', color: 'var(--gold-light)' }}>in real time.</em>
          </h1>
          <p
            style={{
              fontFamily: 'var(--fb)',
              fontSize: 14,
              color: 'rgba(255,255,255,0.5)',
              margin: 0,
              maxWidth: 520,
            }}
          >
            {summaryQuery.data?.total_teams ?? '—'} team units tracked. Signals updated daily
            from calendar, activity, and sprint data.
          </p>
        </div>
      </section>

      {/* Slicer bar */}
      <div
        style={{
          backgroundColor: '#fff',
          borderBottom: '1px solid var(--primary-10)',
          padding: '14px 48px',
          display: 'flex',
          gap: 28,
          alignItems: 'center',
          flexWrap: 'wrap',
        }}
      >
        {/* Period */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={SLICER_LABEL}>Period</span>
          <div style={{ display: 'flex', gap: 4 }}>
            {([7, 14, 30] as const).map(d => (
              <button key={d} onClick={() => setDateRange(d)} style={pillStyle(dateRange === d)}>
                {d}d
              </button>
            ))}
          </div>
        </div>

        {/* Department */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={SLICER_LABEL}>Dept</span>
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            <button onClick={() => handleDeptChange(undefined)} style={pillStyle(!selectedDept)}>
              All
            </button>
            {departments.map(d => (
              <button key={d} onClick={() => handleDeptChange(d)} style={pillStyle(selectedDept === d)}>
                {d}
              </button>
            ))}
          </div>
        </div>

        {/* Team */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={SLICER_LABEL}>Team</span>
          <select
            value={selectedTeam ?? ''}
            onChange={e => setSelectedTeam(e.target.value || undefined)}
            style={{
              fontFamily: 'var(--fb)',
              fontSize: 11,
              color: 'var(--dark)',
              border: '1px solid var(--primary-10)',
              borderRadius: 8,
              padding: '5px 10px',
              background: '#fff',
              cursor: 'pointer',
            }}
          >
            <option value="">All Teams</option>
            {teamOptions.map(t => (
              <option key={t.team_id} value={t.team_id}>
                {t.team_name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* KPI cards */}
      <div style={{ maxWidth: 1300, margin: '0 auto', padding: '32px 48px 0' }}>
        {summaryQuery.isLoading ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 16 }}>
            {[1, 2, 3, 4].map(i => <CardSkeleton key={i} />)}
          </div>
        ) : summaryQuery.data ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 16 }}>
            <KpiCard value={summaryQuery.data.total_teams} label="Total Teams" />
            <KpiCard value={summaryQuery.data.green}  label="Healthy"   sub="AFS 0–39" />
            <KpiCard value={summaryQuery.data.yellow} label="Monitor"   sub="AFS 40–69" />
            <KpiCard value={summaryQuery.data.red}    label="Intervene" sub="AFS 70–100" />
          </div>
        ) : null}
      </div>

      {/* Shared chart pane */}
      <Section>
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-end',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: 16,
            marginBottom: 24,
          }}
        >
          <div>
            <Eyebrow>AFS Overview</Eyebrow>
            <h2
              style={{
                fontFamily: 'var(--fd)',
                fontSize: 22,
                fontWeight: 300,
                color: 'var(--dark)',
                margin: '0 0 4px',
                lineHeight: 1.25,
              }}
            >
              Fragmentation{' '}
              <em style={{ fontStyle: 'italic' }}>at a glance.</em>
            </h2>
            <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', margin: 0 }}>
              Current AFS snapshot — use scope buttons to compare company, department, or team trends.
            </p>
          </div>

          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            <button onClick={() => handleScopeChange('company')} style={pillStyle(scope === 'company')}>
              Company
            </button>
            <button onClick={() => handleScopeChange('department')} style={pillStyle(scope === 'department')}>
              Department
            </button>
            <button onClick={() => handleScopeChange('team')} style={pillStyle(scope === 'team')}>
              Team
            </button>
          </div>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
            gap: 24,
            alignItems: 'stretch',
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
              <div>
                <Eyebrow>{scope === 'company' ? 'Company AFS' : 'Team AFS'}</Eyebrow>
                <h3
                  style={{
                    fontFamily: 'var(--fd)',
                    fontSize: 18,
                    fontWeight: 300,
                    color: 'var(--dark)',
                    margin: 0,
                    lineHeight: 1.3,
                  }}
                >
                  {scope === 'company'
                    ? 'Average AFS by department'
                    : 'Current AFS by team'}
                </h3>
              </div>
            </div>

            {teamsQuery.isLoading ? (
              <div style={{ height: 260, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--mid)', fontFamily: 'var(--fb)', fontSize: 13 }}>
                Loading…
              </div>
            ) : (
              <AfsBarChart
                entries={barEntries}
                yAxisWidth={scope === 'company' ? 120 : 180}
                height={Math.max(240, barEntries.length * 38 + 40)}
              />
            )}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <div>
              <Eyebrow>Resilience Trend</Eyebrow>
              <h3
                style={{
                  fontFamily: 'var(--fd)',
                  fontSize: 18,
                  fontWeight: 300,
                  color: 'var(--dark)',
                  margin: '0 0 4px',
                  lineHeight: 1.25,
                }}
              >
                AFS over the last{' '}
                <em style={{ fontStyle: 'italic' }}>{dateRange} days.</em>
              </h3>
              <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', margin: 0 }}>
                {scope === 'company'
                  ? 'Showing All Company only.'
                  : scope === 'department'
                  ? selectedDept
                    ? `Showing All Company (navy) + ${selectedDept} (gold).`
                    : 'Choose a department to compare against company AFS.'
                  : selectedDept && selectedTeam && teamLabel
                  ? `Showing All Company (navy) + ${selectedDept} (gold) + ${teamLabel} (orange dashed).`
                  : 'Choose a department and team to show full trend overlay.'}
              </p>
            </div>

            {orgHistQuery.isLoading ? (
              <div style={{ height: 320, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--mid)', fontFamily: 'var(--fb)', fontSize: 13 }}>
                Loading…
              </div>
            ) : orgTrend.length > 0 ? (
              <AfsTrendChart
                orgHistory={orgTrend}
                height={320}
                {...(deptTrend && selectedDept ? { deptHistory: deptTrend, deptLabel: selectedDept } : {})}
                {...(teamTrend && teamLabel ? { teamHistory: teamTrend, teamLabel } : {})}
              />
            ) : null}
          </div>
        </div>
      </Section>

      {/* Team heatmap with sparklines */}
      <Section>
        <div style={{ marginBottom: 20 }}>
          <Eyebrow>Team Heatmap</Eyebrow>
          <h2
            style={{
              fontFamily: 'var(--fd)',
              fontSize: 22,
              fontWeight: 300,
              color: 'var(--dark)',
              margin: '0 0 4px',
              lineHeight: 1.25,
            }}
          >
            Teams by{' '}
            <em style={{ fontStyle: 'italic' }}>resilience zone.</em>
          </h2>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', margin: 0 }}>
            Click any card to view the full 30-day drill-down. Sparkline shows last 7 days.
          </p>
        </div>

        <ErrorBoundary>
          {teamsQuery.isLoading ? (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
                gap: 12,
              }}
            >
              {[1, 2, 3, 4, 5, 6].map(i => <CardSkeleton key={i} />)}
            </div>
          ) : teamsQuery.isError ? (
            <div
              role="alert"
              style={{ color: '#E03448', fontFamily: 'var(--fb)', fontSize: 13 }}
            >
              Failed to load team data. Ensure the backend API is running on port 8000.
            </div>
          ) : (
            <DepartmentHeatmap
              teams={heatmapTeams}
              {...(Object.keys(sparklines).length > 0 ? { sparklines } : {})}
            />
          )}
        </ErrorBoundary>
      </Section>

      {/* Bottom spacer */}
      <div style={{ height: 48 }} />
    </main>
  );
}
