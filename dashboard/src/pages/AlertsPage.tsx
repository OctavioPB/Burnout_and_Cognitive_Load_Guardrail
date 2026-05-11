/**
 * Alerts page — full chronological list of Red Zone alerts
 * with department filter and team drill-down links.
 */

import { useState } from 'react';
import { Eyebrow } from '../components/Eyebrow';
import { AlertFeed } from '../components/AlertFeed';
import { Skeleton } from '../components/LoadingSkeleton';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { useAlerts, useDashboardSummary } from '../hooks/useDashboard';

export function AlertsPage() {
  const [deptFilter, setDeptFilter] = useState<string | undefined>(undefined);
  const alertsQuery  = useAlerts(deptFilter);
  const summaryQuery = useDashboardSummary();

  const departments = summaryQuery.data?.departments.map(d => d.department).sort() ?? [];

  return (
    <main style={{ maxWidth: 1300, margin: '0 auto', padding: '40px 48px' }}>
      {/* Header */}
      <Eyebrow>Alert registry</Eyebrow>
      <h1 style={{ fontFamily: 'var(--fd)', fontSize: 28, fontWeight: 300, color: 'var(--dark)', margin: '0 0 8px' }}>
        Red Zone <em style={{ fontStyle: 'italic' }}>alerts.</em>
      </h1>
      <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', marginBottom: 32 }}>
        Teams that reached the Red Zone for ≥ 3 consecutive days. Sorted by most recent.
      </p>

      {/* Department filter */}
      {departments.length > 0 && (
        <div
          role="group"
          aria-label="Filter by department"
          style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 28 }}
        >
          {['All', ...departments].map(dept => {
            const isActive = dept === 'All' ? !deptFilter : deptFilter === dept;
            return (
              <button
                key={dept}
                onClick={() => setDeptFilter(dept === 'All' ? undefined : dept)}
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
      )}

      {/* Section divider */}
      <div style={{ height: 1, backgroundColor: 'var(--primary-10)', marginBottom: 24 }} />

      <ErrorBoundary>
        {alertsQuery.isLoading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i} style={{ backgroundColor: '#fff', borderRadius: 10, borderLeft: '3px solid var(--primary-10)', padding: '16px 20px' }}>
                <Skeleton height={14} width="30%" style={{ marginBottom: 10 }} />
                <Skeleton height={12} width="60%" />
              </div>
            ))}
          </div>
        ) : alertsQuery.isError ? (
          <div role="alert" style={{ color: '#E03448', fontFamily: 'var(--fb)', fontSize: 13 }}>
            Failed to load alerts. Ensure the backend API is running on port 8000.
          </div>
        ) : alertsQuery.data ? (
          <>
            {alertsQuery.data.length > 0 && (
              <p style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', marginBottom: 16 }}>
                {alertsQuery.data.length} alert{alertsQuery.data.length !== 1 ? 's' : ''} found
                {deptFilter ? ` in ${deptFilter}` : ''}.
              </p>
            )}
            <AlertFeed alerts={alertsQuery.data} />
          </>
        ) : null}
      </ErrorBoundary>
    </main>
  );
}
