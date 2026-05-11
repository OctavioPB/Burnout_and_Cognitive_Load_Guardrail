/**
 * Intervention Panel — HR can accept, dismiss, or customize each suggested
 * intervention for a team, and view efficacy data for applied interventions.
 *
 * RBAC: viewers see applied interventions read-only; only HR Admin and
 * Team Manager can accept or dismiss.
 */

import { useState } from 'react';
import type { InterventionItem } from '../types/domain';
import type { InterventionRecord } from '../types/interventions';
import {
  useApplyIntervention,
  useDismissIntervention,
  useEfficacy,
  useTeamInterventions,
} from '../hooks/useDashboard';
import { useAuthStore } from '../stores/authStore';
import { EfficacyChart } from './EfficacyChart';
import { Skeleton } from './LoadingSkeleton';
import { ZoneBadge } from './ZoneBadge';

// ── Integration label ─────────────────────────────────────────────────────────

const INTEGRATION_LABEL: Record<string, string> = {
  google_calendar: 'Google Calendar',
  jira:            'Jira',
  slack:           'Slack',
  none:            'Internal',
};

const STATUS_COLOR: Record<string, string> = {
  success: '#27B97C',
  failed:  '#E03448',
  skipped: 'var(--mid)',
  pending: 'var(--gold)',
};

// ── Efficacy panel for a single applied intervention ─────────────────────────

function EfficacyPanel({ teamId, interventionId }: { teamId: string; interventionId: string }) {
  const [open, setOpen] = useState(false);
  const { data, isLoading, isError } = useEfficacy(teamId, interventionId, open);

  return (
    <div style={{ marginTop: 10 }}>
      <button
        onClick={() => setOpen(v => !v)}
        style={{
          background: 'none',
          border: '1px solid var(--primary-10)',
          borderRadius: 6,
          color: 'var(--primary)',
          cursor: 'pointer',
          fontFamily: 'var(--fb)',
          fontSize: 10,
          letterSpacing: '1.5px',
          textTransform: 'uppercase',
          padding: '4px 10px',
        }}
        aria-expanded={open}
      >
        {open ? '▲ Hide efficacy' : '▼ View efficacy'}
      </button>

      {open && (
        <div style={{ marginTop: 12 }}>
          {isLoading && <Skeleton height={200} />}
          {isError   && <p style={{ color: '#E03448', fontSize: 12, fontFamily: 'var(--fb)' }}>Failed to load efficacy data.</p>}
          {data && <EfficacyChart data={data} height={220} />}
        </div>
      )}
    </div>
  );
}

// ── Single intervention card ──────────────────────────────────────────────────

interface InterventionCardProps {
  teamId: string;
  item: InterventionItem;
  record: InterventionRecord | undefined;
  canAct: boolean;
}

function InterventionCard({ teamId, item, record, canAct }: InterventionCardProps) {
  const [customMsg, setCustomMsg] = useState('');
  const [showCustom, setShowCustom] = useState(false);

  const applyMutation   = useApplyIntervention(teamId);
  const dismissMutation = useDismissIntervention(teamId);

  const isApplied   = record?.action === 'accepted' || record?.action === 'customized';
  const isDismissed = record?.action === 'dismissed';

  const borderColor = isApplied ? '#27B97C' : isDismissed ? 'var(--primary-10)' : 'var(--gold)';

  return (
    <div
      style={{
        backgroundColor: '#fff',
        borderRadius: 10,
        borderLeft: `3px solid ${borderColor}`,
        padding: '14px 16px',
        boxShadow: '0 1px 3px rgba(0,51,102,0.07)',
        opacity: isDismissed ? 0.55 : 1,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8, marginBottom: 6 }}>
        <div>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 12, fontWeight: 700, color: 'var(--primary)', letterSpacing: '1px', textTransform: 'uppercase', marginBottom: 3 }}>
            {item.title}
          </div>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 12.5, color: '#475569', lineHeight: 1.6, margin: 0 }}>
            {item.description}
          </p>
        </div>

        {/* Status badge */}
        {isApplied && (
          <span style={{ fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, letterSpacing: '1px', textTransform: 'uppercase', color: '#0D5C3A', backgroundColor: '#E0F7EF', borderRadius: 20, padding: '3px 10px', whiteSpace: 'nowrap', flexShrink: 0 }}>
            Applied
          </span>
        )}
        {isDismissed && (
          <span style={{ fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, letterSpacing: '1px', textTransform: 'uppercase', color: 'var(--mid)', backgroundColor: 'var(--light)', borderRadius: 20, padding: '3px 10px', whiteSpace: 'nowrap', flexShrink: 0 }}>
            Dismissed
          </span>
        )}
      </div>

      {/* Applied record details */}
      {record && (
        <div style={{ marginTop: 8, fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', lineHeight: 1.6 }}>
          <span style={{ marginRight: 12 }}>
            {record.actor_name} · {record.applied_at.slice(0, 10)}
          </span>
          {record.integration.integration !== 'none' && (
            <span style={{ color: STATUS_COLOR[record.integration.status] ?? 'var(--mid)' }}>
              {INTEGRATION_LABEL[record.integration.integration] ?? record.integration.integration}
              {' '}
              {record.integration.status === 'success' && record.integration.external_id && (
                <code style={{ fontFamily: 'Courier New', fontSize: 10 }}>
                  #{record.integration.external_id.slice(0, 12)}
                </code>
              )}
            </span>
          )}
        </div>
      )}

      {/* Async-first custom message input */}
      {canAct && !record && item.id === 'async_first_week' && showCustom && (
        <textarea
          value={customMsg}
          onChange={e => setCustomMsg(e.target.value)}
          placeholder="Write the message HR will post to the team's Slack channel…"
          rows={3}
          style={{
            width: '100%', marginTop: 10, padding: '8px 10px',
            fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--dark)',
            border: '1px solid var(--primary-10)', borderRadius: 6,
            resize: 'vertical', outline: 'none', boxSizing: 'border-box',
          }}
          aria-label="Slack message for Async-First Week"
        />
      )}

      {/* Action buttons */}
      {canAct && !record && (
        <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
          {item.id === 'async_first_week' && !showCustom ? (
            <button
              onClick={() => setShowCustom(true)}
              style={btnStyle('primary')}
            >
              Write message & Apply
            </button>
          ) : (
            <button
              disabled={applyMutation.isPending || (item.id === 'async_first_week' && !customMsg.trim())}
              onClick={() => applyMutation.mutate({
                intervention_id: item.id,
                ...(item.id === 'async_first_week' ? { customization: customMsg } : {}),
              })}
              style={btnStyle('primary', applyMutation.isPending)}
              aria-busy={applyMutation.isPending}
            >
              {applyMutation.isPending ? 'Applying…' : 'Accept'}
            </button>
          )}
          <button
            disabled={dismissMutation.isPending}
            onClick={() => dismissMutation.mutate({ intervention_id: item.id })}
            style={btnStyle('ghost', dismissMutation.isPending)}
            aria-busy={dismissMutation.isPending}
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Efficacy view for applied interventions */}
      {isApplied && <EfficacyPanel teamId={teamId} interventionId={item.id} />}
    </div>
  );
}

function btnStyle(variant: 'primary' | 'ghost', disabled = false): React.CSSProperties {
  return {
    background: variant === 'primary' ? 'var(--primary)' : 'none',
    color:      variant === 'primary' ? '#fff' : 'var(--mid)',
    border:     variant === 'primary' ? 'none' : '1px solid var(--primary-10)',
    borderRadius: 6,
    cursor: disabled ? 'not-allowed' : 'pointer',
    fontFamily: 'var(--fb)',
    fontSize: 10,
    fontWeight: 600,
    letterSpacing: '1.5px',
    textTransform: 'uppercase',
    padding: '5px 12px',
    opacity: disabled ? 0.5 : 1,
    transition: 'opacity 0.1s',
  };
}

// ── Panel ─────────────────────────────────────────────────────────────────────

interface InterventionPanelProps {
  teamId: string;
  suggestedInterventions: InterventionItem[];
}

export function InterventionPanel({ teamId, suggestedInterventions }: InterventionPanelProps) {
  const { user } = useAuthStore();
  const { data: records, isLoading } = useTeamInterventions(teamId);

  const canAct = user?.role === 'hr_admin' || user?.role === 'team_manager';

  if (isLoading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {[1, 2].map(i => <Skeleton key={i} height={80} borderRadius={10} />)}
      </div>
    );
  }

  if (suggestedInterventions.length === 0 && (!records || records.length === 0)) {
    return (
      <div style={{ backgroundColor: '#E0F7EF', borderRadius: 10, padding: '14px', textAlign: 'center' }}>
        <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: '#0D5C3A', fontWeight: 600, marginBottom: 2 }}>No interventions required</div>
        <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: '#0D5C3A' }}>This team is in a healthy zone.</div>
      </div>
    );
  }

  // Show all suggested + any previously dismissed ones that aren't in the current suggestions
  const allIds = new Set([
    ...suggestedInterventions.map(i => i.id),
    ...(records ?? []).map(r => r.intervention_id),
  ]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {[...allIds].map(id => {
        const suggestion = suggestedInterventions.find(i => i.id === id) ?? {
          id,
          title: (records ?? []).find(r => r.intervention_id === id)?.intervention_title ?? id,
          description: '',
        };
        const record = (records ?? []).filter(r => r.intervention_id === id).at(-1);
        return (
          <InterventionCard
            key={id}
            teamId={teamId}
            item={suggestion}
            record={record}
            canAct={canAct}
          />
        );
      })}
    </div>
  );
}
