/**
 * Dashboard Home — org-wide KPI summary + department heatmap.
 *
 * Layout:
 *  1. Dark hero section with AFS overview stats
 *  2. KPI row (total teams, green/yellow/red counts, active alerts)
 *  3. Department heatmap with filter
 */

import { useState } from 'react';
import { Eyebrow } from '../components/Eyebrow';
import { KpiCard } from '../components/KpiCard';
import { DepartmentHeatmap } from '../components/DepartmentHeatmap';
import { CardSkeleton } from '../components/LoadingSkeleton';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { useDashboardSummary, useTeams } from '../hooks/useDashboard';
import type { DeptSummary } from '../types/domain';

function HeroSection({ green, yellow, red, active_alerts, total_teams }:
  { green: number; yellow: number; red: number; active_alerts: number; total_teams: number }) {
  return (
    <section
      className="hero-dark"
      aria-labelledby="hero-title"
      style={{ padding: '56px 48px' }}
    >
      <div style={{ maxWidth: 1300, margin: '0 auto' }}>
        <h1
          id="hero-title"
          style={{
            fontFamily: 'var(--fd)',
            fontSize: 32,
            fontWeight: 300,
            color: '#fff',
            margin: '0 0 12px',
            lineHeight: 1.25,
          }}
        >
          Org-wide resilience, <em style={{ fontStyle: 'italic', color: 'var(--gold-light)' }}>in real time.</em>
        </h1>
        <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'rgba(255,255,255,0.55)', marginBottom: 40, maxWidth: 560 }}>
          {total_teams} team units tracked. Signals updated daily from calendar, activity, and sprint data.
        </p>

        {/* Stat row */}
        <div style={{ display: 'flex', gap: 32, flexWrap: 'wrap' }}>
          {[
            { value: green,         label: 'Healthy teams' },
            { value: yellow,        label: 'Teams to monitor' },
            { value: red,           label: 'Teams to intervene' },
            { value: active_alerts, label: 'Active alerts' },
          ].map(stat => (
            <div key={stat.label} style={{ borderLeft: '2px solid var(--gold)', paddingLeft: 18 }}>
              <div style={{ fontFamily: 'var(--fd)', fontSize: 34, fontWeight: 300, color: 'var(--gold-light)', lineHeight: 1, marginBottom: 8 }}>
                {stat.value}
              </div>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'rgba(255,255,255,0.5)', lineHeight: 1.55 }}>
                {stat.label}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function DeptFilter({ departments, selected, onChange }: {
  departments: DeptSummary[];
  selected: string | undefined;
  onChange: (dept: string | undefined) => void;
}) {
  const allDepts = ['All', ...departments.map(d => d.department).sort()];
  return (
    <div
      role="group"
      aria-label="Filter by department"
      style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 28 }}
    >
      {allDepts.map(dept => {
        const isActive = dept === 'All' ? !selected : selected === dept;
        return (
          <button
            key={dept}
            onClick={() => onChange(dept === 'All' ? undefined : dept)}
            aria-pressed={isActive}
            style={{
              background: isActive ? 'var(--primary)' : '#fff',
              color: isActive ? '#fff' : 'var(--primary)',
              border: `1px solid ${isActive ? 'var(--primary)' : 'var(--primary-10)'}`,
              borderRadius: 20,
              padding: '5px 14px',
              fontFamily: 'var(--fb)',
              fontSize: 11,
              fontWeight: 500,
              letterSpacing: '1px',
              cursor: 'pointer',
              transition: 'all 0.15s',
            }}
          >
            {dept}
          </button>
        );
      })}
    </div>
  );
}

export function DashboardHome() {
  const [deptFilter, setDeptFilter] = useState<string | undefined>(undefined);
  const summaryQuery = useDashboardSummary();
  const teamsQuery   = useTeams(deptFilter);

  return (
    <main>
      {/* Hero */}
      {summaryQuery.isLoading ? (
        <div className="hero-dark" style={{ padding: '56px 48px' }}>
          <div style={{ maxWidth: 1300, margin: '0 auto', display: 'flex', gap: 32 }}>
            {[1, 2, 3, 4].map(i => (
              <div key={i} style={{ borderLeft: '2px solid var(--gold)', paddingLeft: 18, width: 120 }}>
                <div style={{ height: 34, width: 48, borderRadius: 4, backgroundColor: 'rgba(255,255,255,0.08)', marginBottom: 8 }} />
                <div style={{ height: 12, width: 100, borderRadius: 4, backgroundColor: 'rgba(255,255,255,0.06)' }} />
              </div>
            ))}
          </div>
        </div>
      ) : summaryQuery.data ? (
        <HeroSection {...summaryQuery.data} />
      ) : null}

      {/* KPI row + heatmap */}
      <div style={{ maxWidth: 1300, margin: '0 auto', padding: '40px 48px' }}>

        {/* KPI cards */}
        {summaryQuery.isLoading ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 16, marginBottom: 40 }}>
            {[1, 2, 3, 4].map(i => <CardSkeleton key={i} />)}
          </div>
        ) : summaryQuery.data ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 16, marginBottom: 40 }}>
            <KpiCard value={summaryQuery.data.total_teams} label="Total Teams" />
            <KpiCard value={summaryQuery.data.green}  label="Healthy"    sub="AFS 0–39" />
            <KpiCard value={summaryQuery.data.yellow} label="Monitor"    sub="AFS 40–69" />
            <KpiCard value={summaryQuery.data.red}    label="Intervene"  sub="AFS 70–100" />
          </div>
        ) : null}

        {/* Section title + filter */}
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16, marginBottom: 12 }}>
          <div>
            <Eyebrow>Department heatmap</Eyebrow>
            <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', margin: '0 0 4px', lineHeight: 1.25 }}>
              Teams by <em style={{ fontStyle: 'italic' }}>resilience zone.</em>
            </h2>
            <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', margin: 0 }}>
              Click any team card to view the 30-day AFS trend.
            </p>
          </div>
        </div>

        {summaryQuery.data && (
          <DeptFilter
            departments={summaryQuery.data.departments}
            selected={deptFilter}
            onChange={setDeptFilter}
          />
        )}

        <ErrorBoundary>
          {teamsQuery.isLoading ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12 }}>
              {[1, 2, 3, 4, 5, 6].map(i => <CardSkeleton key={i} />)}
            </div>
          ) : teamsQuery.isError ? (
            <div role="alert" style={{ color: '#E03448', fontFamily: 'var(--fb)', fontSize: 13 }}>
              Failed to load team data. Ensure the backend API is running on port 8000.
            </div>
          ) : teamsQuery.data ? (
            <DepartmentHeatmap teams={teamsQuery.data} />
          ) : null}
        </ErrorBoundary>
      </div>
    </main>
  );
}
