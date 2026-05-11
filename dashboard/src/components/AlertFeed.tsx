/**
 * Alert feed — chronological list of Red Zone alerts with
 * timestamps, consecutive day count, and triggered interventions.
 */

import { useNavigate } from 'react-router-dom';
import { format, parseISO } from 'date-fns';
import type { AlertRecord } from '../types/domain';
import { ZoneBadge } from './ZoneBadge';

function InterventionPill({ title }: { title: string }) {
  return (
    <span
      style={{
        display: 'inline-block',
        fontFamily: 'var(--fb)',
        fontSize: 10,
        fontWeight: 500,
        color: 'var(--primary)',
        backgroundColor: 'var(--primary-10)',
        borderRadius: 20,
        padding: '3px 10px',
        whiteSpace: 'nowrap',
      }}
    >
      {title}
    </span>
  );
}

function AlertRow({ alert }: { alert: AlertRecord }) {
  const navigate = useNavigate();
  const date = format(parseISO(alert.trigger_date), 'MMM d, yyyy');

  return (
    <li
      style={{
        backgroundColor: '#fff',
        borderRadius: 10,
        borderLeft: '3px solid #E03448',
        padding: '16px 20px',
        boxShadow: '0 1px 3px rgba(0,51,102,0.06)',
        listStyle: 'none',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
        <div>
          <button
            onClick={() => navigate(`/team/${alert.team_id}`)}
            style={{
              background: 'none',
              border: 'none',
              padding: 0,
              cursor: 'pointer',
              fontFamily: 'var(--fb)',
              fontSize: 14,
              fontWeight: 600,
              color: 'var(--primary)',
              textDecoration: 'underline',
              textDecorationColor: 'transparent',
              transition: 'text-decoration-color 0.15s',
            }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.textDecorationColor = 'var(--primary)'; }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.textDecorationColor = 'transparent'; }}
            aria-label={`View ${alert.team_name} drill-down`}
          >
            {alert.team_name}
          </button>
          <span
            style={{
              fontFamily: 'var(--fb)',
              fontSize: 11,
              color: 'var(--mid)',
              marginLeft: 10,
            }}
          >
            {alert.department}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <ZoneBadge zone="red" label={`${alert.consecutive_red_days}d Red`} />
          <span style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', whiteSpace: 'nowrap' }}>
            {date}
          </span>
        </div>
      </div>

      {alert.interventions.length > 0 && (
        <div style={{ marginTop: 10, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {alert.interventions.map(i => (
            <InterventionPill key={i.id} title={i.title} />
          ))}
        </div>
      )}
    </li>
  );
}

interface AlertFeedProps {
  alerts: AlertRecord[];
  maxRows?: number;
}

export function AlertFeed({ alerts, maxRows }: AlertFeedProps) {
  const visible = maxRows ? alerts.slice(0, maxRows) : alerts;

  if (visible.length === 0) {
    return (
      <div
        style={{
          textAlign: 'center',
          padding: '36px 0',
          color: 'var(--mid)',
          fontFamily: 'var(--fb)',
          fontSize: 14,
        }}
        role="status"
      >
        No alerts to display.
      </div>
    );
  }

  return (
    <ul
      aria-label="Alert feed"
      style={{ padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 10 }}
    >
      {visible.map(a => (
        <AlertRow key={a.alert_id} alert={a} />
      ))}
    </ul>
  );
}
