/**
 * HR Admin page — database management for demo / staging environments.
 *
 * Two operations:
 *   Reset  — restore the default 12-team dataset immediately.
 *   Seed   — rebuild from a custom team roster, stress profile, and history window.
 *
 * Both require the hr_admin role (enforced server-side; client also guards on mount).
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eyebrow } from '../components/Eyebrow';
import { useAuthStore } from '../stores/authStore';
import {
  useResetStore,
  useSeedStore,
  type AdminTeamEntry,
  type AdminSeedRequest,
} from '../hooks/useDashboard';

// ── Brand tokens ──────────────────────────────────────────────────────────────

const N  = '#003366';
const NM = '#385A87';
const NL = '#6B7FA3';
const NB = 'rgba(0,51,102,0.10)';
const G  = '#C8982A';
const GN = '#27B97C';
const RD = '#E03448';
const DK = '#001F3F';
const WH = '#ffffff';

// ── Constants ─────────────────────────────────────────────────────────────────

const DEPARTMENTS = ['Engineering', 'Product', 'Design', 'Data', 'Marketing', 'HR', 'Finance', 'Operations'];

const DEFAULT_TEAMS: AdminTeamEntry[] = [
  { team_id: 'T-01', team_name: 'Frontend Engineering', department: 'Engineering' },
  { team_id: 'T-02', team_name: 'Backend Engineering',  department: 'Engineering' },
  { team_id: 'T-03', team_name: 'Infrastructure',       department: 'Engineering' },
  { team_id: 'T-04', team_name: 'Mobile Engineering',   department: 'Engineering' },
  { team_id: 'T-05', team_name: 'Core Product',         department: 'Product'     },
  { team_id: 'T-06', team_name: 'Growth Product',       department: 'Product'     },
  { team_id: 'T-07', team_name: 'Platform Product',     department: 'Product'     },
  { team_id: 'T-08', team_name: 'UX Design',            department: 'Design'      },
  { team_id: 'T-09', team_name: 'Brand Design',         department: 'Design'      },
  { team_id: 'T-10', team_name: 'Analytics',            department: 'Data'        },
  { team_id: 'T-11', team_name: 'ML Engineering',       department: 'Data'        },
  { team_id: 'T-12', team_name: 'Business Intelligence', department: 'Data'       },
];

const STRESS_META = {
  low:   { label: 'Low Stress',   desc: 'Most teams operate in the Green zone. Suitable for demonstrating a healthy org baseline.', green: 70, yellow: 25, red: 5 },
  mixed: { label: 'Mixed',        desc: 'Realistic distribution across all three zones. The default demo dataset.', green: 40, yellow: 35, red: 25 },
  high:  { label: 'High Stress',  desc: 'Majority of teams in Yellow or Red. Useful for demonstrating alert workflows.', green: 5, yellow: 30, red: 65 },
} as const;

type StressProfile = keyof typeof STRESS_META;

// ── Shared style helpers ──────────────────────────────────────────────────────

function pill(active: boolean, danger = false): React.CSSProperties {
  return {
    background: active ? (danger ? RD : N) : WH,
    color:      active ? WH : (danger ? RD : N),
    border:     `1px solid ${active ? (danger ? RD : N) : NB}`,
    borderRadius: 20,
    padding: '5px 16px',
    fontFamily: 'var(--fb)',
    fontSize: 11,
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.15s',
    letterSpacing: '0.5px',
  };
}

const td: React.CSSProperties = {
  padding: '10px 12px',
  fontFamily: 'var(--fb)',
  fontSize: 12,
  color: DK,
  borderBottom: `1px solid ${NB}`,
  verticalAlign: 'middle',
};

// ── Zone preview bar ──────────────────────────────────────────────────────────

function ZoneBar({ green, yellow, red }: { green: number; yellow: number; red: number }) {
  return (
    <div style={{ marginTop: 12 }}>
      <div style={{ display: 'flex', borderRadius: 6, overflow: 'hidden', height: 12 }}>
        <div style={{ flex: green,  background: GN }} title={`~${green}% green`} />
        <div style={{ flex: yellow, background: G  }} title={`~${yellow}% yellow`} />
        <div style={{ flex: red,    background: RD }} title={`~${red}% red`} />
      </div>
      <div style={{ display: 'flex', gap: 16, marginTop: 8 }}>
        {[['Green', GN, green], ['Yellow', G, yellow], ['Red', RD, red]].map(([label, color, pct]) => (
          <div key={label as string} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: color as string }} />
            <span style={{ fontFamily: 'var(--fb)', fontSize: 11, color: NL }}>~{pct}% {label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Inline confirm button ─────────────────────────────────────────────────────

function ConfirmButton({
  label, confirmLabel = 'Confirm', danger = false, loading = false, onConfirm,
}: {
  label: string;
  confirmLabel?: string;
  danger?: boolean;
  loading?: boolean;
  onConfirm: () => void;
}) {
  const [armed, setArmed] = useState(false);

  if (loading) {
    return (
      <button disabled style={{ ...pill(true, danger), opacity: 0.6 }}>
        Working…
      </button>
    );
  }

  if (armed) {
    return (
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <span style={{ fontFamily: 'var(--fb)', fontSize: 11, color: NL }}>Are you sure?</span>
        <button
          onClick={() => { setArmed(false); onConfirm(); }}
          style={{ ...pill(true, danger) }}
        >
          {confirmLabel}
        </button>
        <button onClick={() => setArmed(false)} style={pill(false)}>
          Cancel
        </button>
      </div>
    );
  }

  return (
    <button onClick={() => setArmed(true)} style={pill(false, danger)}>
      {label}
    </button>
  );
}

// ── Result banner ─────────────────────────────────────────────────────────────

function ResultBanner({ result }: { result: { ok: boolean; message: string } | null }) {
  if (!result) return null;
  return (
    <div style={{
      marginTop: 16,
      padding: '12px 16px',
      background: result.ok ? '#EEF9F4' : '#FEF2F4',
      border: `1px solid ${result.ok ? GN + '55' : RD + '55'}`,
      borderRadius: 8,
      fontFamily: 'var(--fb)',
      fontSize: 12,
      color: result.ok ? '#1A5C3A' : RD,
    }}>
      {result.message}
    </div>
  );
}

// ── Reset section ─────────────────────────────────────────────────────────────

function ResetSection() {
  const reset = useResetStore();
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);

  const handleReset = () => {
    reset.mutate(undefined, {
      onSuccess: r  => setResult({ ok: true,  message: r.message }),
      onError:   () => setResult({ ok: false, message: 'Reset failed. Check the API server.' }),
    });
  };

  return (
    <div style={{
      border: `1px solid ${RD}33`,
      borderLeft: `3px solid ${RD}`,
      borderRadius: 10,
      padding: 24,
      background: '#FEF8F8',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
        <div style={{ flex: '1 1 320px' }}>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 11, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', color: RD, marginBottom: 6 }}>
            Destructive
          </div>
          <div style={{ fontFamily: 'var(--fd)', fontSize: 18, fontWeight: 300, color: DK, marginBottom: 8 }}>
            Reset to default dataset
          </div>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: NL, lineHeight: 1.65, maxWidth: 560 }}>
            Restores all 12 original teams across Engineering, Product, Design, and Data with
            their default seeded trajectories and a 30-day mixed stress history.
            All custom seeds and any in-memory intervention state will be lost.
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', paddingTop: 8 }}>
          <ConfirmButton
            label="Reset to Defaults"
            confirmLabel="Yes, reset"
            danger
            loading={reset.isPending}
            onConfirm={handleReset}
          />
        </div>
      </div>
      <ResultBanner result={result} />
    </div>
  );
}

// ── Team builder ──────────────────────────────────────────────────────────────

function TeamBuilder({
  teams,
  onChange,
}: {
  teams: AdminTeamEntry[];
  onChange: (teams: AdminTeamEntry[]) => void;
}) {
  const nextId = () => {
    const nums = teams.map(t => parseInt(t.team_id.replace('T-', ''), 10)).filter(n => !isNaN(n));
    return `T-${String(Math.max(0, ...nums) + 1).padStart(2, '0')}`;
  };

  const update = (idx: number, field: keyof AdminTeamEntry, val: string) => {
    const next = teams.map((t, i) => i === idx ? { ...t, [field]: val } : t);
    onChange(next);
  };

  const remove = (idx: number) => onChange(teams.filter((_, i) => i !== idx));

  const add = () => onChange([...teams, { team_id: nextId(), team_name: 'New Team', department: 'Engineering' }]);

  return (
    <div>
      <div style={{ overflowX: 'auto', borderRadius: 8, boxShadow: '0 1px 4px rgba(0,51,102,0.06)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', background: WH, minWidth: 520 }}>
          <thead>
            <tr style={{ background: N }}>
              {['ID', 'Team Name', 'Department', ''].map(h => (
                <th key={h} style={{ padding: '10px 12px', fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 500, letterSpacing: '2px', textTransform: 'uppercase', color: WH, textAlign: 'left' }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {teams.map((t, i) => (
              <tr key={t.team_id} style={{ background: i % 2 === 0 ? WH : '#F8F9FC' }}>
                <td style={{ ...td, fontFamily: 'Courier New, monospace', color: NL, width: 60 }}>{t.team_id}</td>
                <td style={{ ...td }}>
                  <input
                    value={t.team_name}
                    onChange={e => update(i, 'team_name', e.target.value)}
                    style={{
                      width: '100%', fontFamily: 'var(--fb)', fontSize: 12, color: DK,
                      border: `1px solid ${NB}`, borderRadius: 6, padding: '5px 8px',
                      background: 'transparent', outline: 'none', boxSizing: 'border-box',
                    }}
                  />
                </td>
                <td style={{ ...td }}>
                  <select
                    value={t.department}
                    onChange={e => update(i, 'department', e.target.value)}
                    style={{
                      fontFamily: 'var(--fb)', fontSize: 12, color: DK,
                      border: `1px solid ${NB}`, borderRadius: 6, padding: '5px 8px',
                      background: WH, cursor: 'pointer',
                    }}
                  >
                    {DEPARTMENTS.map(d => <option key={d} value={d}>{d}</option>)}
                  </select>
                </td>
                <td style={{ ...td, width: 40, textAlign: 'center' }}>
                  <button
                    onClick={() => remove(i)}
                    disabled={teams.length <= 1}
                    aria-label={`Remove ${t.team_name}`}
                    style={{
                      background: 'none', border: 'none', cursor: teams.length > 1 ? 'pointer' : 'not-allowed',
                      color: teams.length > 1 ? RD : NB, fontSize: 16, padding: '0 4px',
                      fontFamily: 'var(--fb)',
                    }}
                  >
                    ×
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <button
        onClick={add}
        style={{
          marginTop: 10, fontFamily: 'var(--fb)', fontSize: 11, fontWeight: 600,
          color: N, background: 'none', border: `1px dashed ${NM}`, borderRadius: 6,
          padding: '6px 16px', cursor: 'pointer', letterSpacing: '0.5px',
        }}
      >
        + Add Team
      </button>
    </div>
  );
}

// ── Seed section ──────────────────────────────────────────────────────────────

function SeedSection() {
  const seed = useSeedStore();
  const [teams, setTeams]               = useState<AdminTeamEntry[]>(DEFAULT_TEAMS);
  const [profile, setProfile]           = useState<StressProfile>('mixed');
  const [historyDays, setHistoryDays]   = useState<7 | 14 | 30>(30);
  const [result, setResult]             = useState<{ ok: boolean; message: string } | null>(null);

  const handleSeed = () => {
    const body: AdminSeedRequest = {
      teams,
      stress_profile: profile,
      history_days: historyDays,
    };
    seed.mutate(body, {
      onSuccess: r  => setResult({ ok: true,  message: r.message }),
      onError:   () => setResult({ ok: false, message: 'Seed failed. Check the API server.' }),
    });
  };

  const meta = STRESS_META[profile];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>

      {/* Stress profile */}
      <div>
        <div style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', color: NL, marginBottom: 12 }}>
          Stress Profile
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 14 }}>
          {(Object.keys(STRESS_META) as StressProfile[]).map(p => (
            <button key={p} onClick={() => setProfile(p)} style={pill(profile === p)}>
              {STRESS_META[p].label}
            </button>
          ))}
        </div>
        <p style={{ fontFamily: 'var(--fb)', fontSize: 12, color: NL, margin: '0 0 8px', lineHeight: 1.5 }}>
          {meta.desc}
        </p>
        <ZoneBar green={meta.green} yellow={meta.yellow} red={meta.red} />
      </div>

      <div style={{ height: 1, background: NB }} />

      {/* History window */}
      <div>
        <div style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', color: NL, marginBottom: 12 }}>
          History Window
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {([7, 14, 30] as const).map(d => (
            <button key={d} onClick={() => setHistoryDays(d)} style={pill(historyDays === d)}>
              {d} days
            </button>
          ))}
        </div>
      </div>

      <div style={{ height: 1, background: NB }} />

      {/* Team roster */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 12 }}>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', color: NL }}>
            Team Roster
          </div>
          <span style={{ fontFamily: 'var(--fb)', fontSize: 11, color: NL }}>
            {teams.length} team{teams.length !== 1 ? 's' : ''}
          </span>
        </div>
        <TeamBuilder teams={teams} onChange={setTeams} />
        <button
          onClick={() => setTeams(DEFAULT_TEAMS)}
          style={{ marginTop: 8, background: 'none', border: 'none', fontFamily: 'var(--fb)', fontSize: 11, color: NL, cursor: 'pointer', textDecoration: 'underline', padding: 0 }}
        >
          Restore default roster
        </button>
      </div>

      <div style={{ height: 1, background: NB }} />

      {/* Apply */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 20, flexWrap: 'wrap' }}>
        <ConfirmButton
          label="Apply Seed Configuration"
          confirmLabel="Yes, rebuild dataset"
          loading={seed.isPending}
          onConfirm={handleSeed}
        />
        <span style={{ fontFamily: 'var(--fb)', fontSize: 11, color: NL }}>
          {teams.length} team{teams.length !== 1 ? 's' : ''} · {profile} stress · {historyDays}-day history
        </span>
      </div>

      <ResultBanner result={result} />
    </div>
  );
}

// ── Page root ─────────────────────────────────────────────────────────────────

export function HrAdminPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();

  useEffect(() => {
    if (user && user.role !== 'hr_admin') navigate('/dashboard', { replace: true });
  }, [user, navigate]);

  if (!user || user.role !== 'hr_admin') return null;

  return (
    <main style={{ maxWidth: 900, margin: '0 auto', padding: '40px 48px' }}>
      <Eyebrow>Demo Tools</Eyebrow>
      <h1 style={{ fontFamily: 'var(--fd)', fontSize: 28, fontWeight: 300, color: DK, margin: '0 0 8px' }}>
        HR Admin <em style={{ fontStyle: 'italic' }}>panel.</em>
      </h1>
      <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: NL, marginBottom: 32, maxWidth: 600 }}>
        Manage the staging dataset. Reset to the default 12-team configuration or build a
        custom seed with a specific team roster, stress distribution, and history window.
      </p>

      <div style={{ height: 1, background: NB, marginBottom: 40 }} />

      {/* Reset */}
      <section aria-labelledby="reset-heading" style={{ marginBottom: 48 }}>
        <Eyebrow>Quick Action</Eyebrow>
        <h2 id="reset-heading" style={{ fontFamily: 'var(--fd)', fontSize: 20, fontWeight: 300, color: DK, margin: '4px 0 20px' }}>
          Reset dataset
        </h2>
        <ResetSection />
      </section>

      {/* Seed */}
      <section aria-labelledby="seed-heading">
        <Eyebrow>Custom Seed</Eyebrow>
        <h2 id="seed-heading" style={{ fontFamily: 'var(--fd)', fontSize: 20, fontWeight: 300, color: DK, margin: '4px 0 20px' }}>
          Build a custom dataset
        </h2>
        <div style={{ border: `1px solid ${NB}`, borderRadius: 10, padding: 28, background: WH }}>
          <SeedSection />
        </div>
      </section>
    </main>
  );
}
