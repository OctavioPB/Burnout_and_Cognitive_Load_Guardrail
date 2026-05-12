/**
 * Audit Log page — HR Admins only.
 *
 * Shows who viewed which team data and when, and all intervention
 * accept/dismiss actions.  The API enforces the HR Admin role server-side;
 * the frontend also redirects non-admin users on mount.
 */

import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { format, parseISO } from 'date-fns';
import { Eyebrow } from '../components/Eyebrow';
import { Skeleton } from '../components/LoadingSkeleton';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { useAuditLog } from '../hooks/useDashboard';
import { useAuthStore } from '../stores/authStore';
import type { AuditLogEntry } from '../types/interventions';

const ACTION_LABEL: Record<string, string> = {
  view_dashboard:       'Viewed Dashboard',
  view_team:            'Viewed Team',
  view_alerts:          'Viewed Alert Feed',
  view_audit:           'Viewed Audit Log',
  apply_intervention:   'Applied Intervention',
  dismiss_intervention: 'Dismissed Intervention',
};

const ACTION_COLOR: Record<string, string> = {
  apply_intervention:   '#27B97C',
  dismiss_intervention: 'var(--mid)',
  view_dashboard:       'var(--primary-60)',
  view_team:            'var(--primary-60)',
  view_alerts:          '#F07020',
  view_audit:           '#7C4DBD',
};

function AuditRow({ entry }: { entry: AuditLogEntry }) {
  const ts = format(parseISO(entry.timestamp), 'MMM d, yyyy HH:mm');
  const color = ACTION_COLOR[entry.action] ?? 'var(--mid)';
  return (
    <>
      <td style={tdStyle}>{ts}</td>
      <td style={tdStyle}>
        <div style={{ fontWeight: 600 }}>{entry.actor_name}</div>
        <div style={{ fontSize: 10, color: 'var(--mid)', textTransform: 'uppercase', letterSpacing: '1px' }}>{entry.actor_role}</div>
      </td>
      <td style={tdStyle}>
        <span style={{ color, fontWeight: 600 }}>{ACTION_LABEL[entry.action] ?? entry.action}</span>
      </td>
      <td style={{ ...tdStyle, fontFamily: 'Courier New, monospace', fontSize: 12 }}>{entry.resource}</td>
      <td style={{ ...tdStyle, color: 'var(--mid)', fontSize: 11 }}>{entry.detail || '—'}</td>
    </>
  );
}

const tdStyle: React.CSSProperties = {
  padding: '12px 16px',
  fontFamily: 'var(--fb)',
  fontSize: 13,
  color: 'var(--dark)',
  borderBottom: '1px solid var(--primary-10)',
  verticalAlign: 'top',
};

export function AuditLogPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const { data, isLoading, isError } = useAuditLog(200);

  // Client-side guard: redirect non-admins immediately
  useEffect(() => {
    if (user && user.role !== 'hr_admin') {
      navigate('/dashboard', { replace: true });
    }
  }, [user, navigate]);

  if (!user || user.role !== 'hr_admin') return null;

  return (
    <main style={{ maxWidth: 1300, margin: '0 auto', padding: '40px 48px' }}>
      <Eyebrow>Compliance</Eyebrow>
      <h1 style={{ fontFamily: 'var(--fd)', fontSize: 28, fontWeight: 300, color: 'var(--dark)', margin: '0 0 8px' }}>
        Audit <em style={{ fontStyle: 'italic' }}>log.</em>
      </h1>
      <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', marginBottom: 32 }}>
        Every dashboard read and intervention action, logged with actor identity and timestamp.
      </p>

      <div style={{ height: 1, backgroundColor: 'var(--primary-10)', marginBottom: 24 }} />

      <ErrorBoundary>
        {isLoading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {[1, 2, 3, 4, 5, 6].map(i => <Skeleton key={i} height={44} />)}
          </div>
        ) : isError ? (
          <div role="alert" style={{ color: '#E03448', fontFamily: 'var(--fb)', fontSize: 13 }}>
            Failed to load audit log. Ensure the backend API is running.
          </div>
        ) : data ? (
          <>
            <p style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', marginBottom: 12 }}>
              {data.length} event{data.length !== 1 ? 's' : ''} recorded.
            </p>

            <div style={{ overflowX: 'auto', borderRadius: 10, boxShadow: '0 1px 4px rgba(0,51,102,0.08)' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', backgroundColor: '#fff' }}>
                <thead>
                  <tr style={{ backgroundColor: 'var(--primary)' }}>
                    {['Timestamp', 'Actor', 'Action', 'Resource', 'Detail'].map(h => (
                      <th
                        key={h}
                        scope="col"
                        style={{
                          padding: '12px 16px',
                          fontFamily: 'var(--fb)',
                          fontSize: 10,
                          fontWeight: 500,
                          letterSpacing: '2px',
                          textTransform: 'uppercase',
                          color: '#fff',
                          textAlign: 'left',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.length === 0 ? (
                    <tr>
                      <td colSpan={5} style={{ ...tdStyle, textAlign: 'center', color: 'var(--mid)' }}>
                        No audit events recorded yet.
                      </td>
                    </tr>
                  ) : (
                    data.map((entry, idx) => (
                      <tr
                        key={entry.log_id}
                        style={{ backgroundColor: idx % 2 === 0 ? '#fff' : 'var(--primary-10)' }}
                      >
                        <AuditRow entry={entry} />
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </>
        ) : null}
      </ErrorBoundary>
    </main>
  );
}
