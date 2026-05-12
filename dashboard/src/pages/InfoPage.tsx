/**
 * InfoPage — dual-view platform documentation.
 *
 * Business View: HR-focused narrative — problem, solution, workflow, compliance.
 * Engineering View: Architecture, tech stack, ML pipeline, security.
 */

import { useState, Fragment } from 'react';
import { Eyebrow } from '../components/Eyebrow';

type View = 'business' | 'engineering';

// ── Brand tokens ──────────────────────────────────────────────────────────────

const N   = '#003366';
const NM  = '#385A87';
const NL  = '#6B7FA3';
const NB  = 'rgba(0,51,102,0.10)';
const G   = '#C8982A';
const GN  = '#27B97C';
const RD  = '#E03448';
const OR  = '#F07020';
const DK  = '#001F3F';
const WH  = '#ffffff';

// ── Layout helpers ────────────────────────────────────────────────────────────

const MAX_W = 1100;
const HR: React.CSSProperties = { height: 1, backgroundColor: NB, margin: '32px 0' };

function Sec({ children, tinted = false }: { children: React.ReactNode; tinted?: boolean }) {
  return (
    <div style={{ backgroundColor: tinted ? '#F8F9FC' : WH, borderBottom: `1px solid ${NB}` }}>
      <div style={{ maxWidth: MAX_W, margin: '0 auto', padding: '56px 48px' }}>{children}</div>
    </div>
  );
}

function SH({ eyebrow, title, sub }: { eyebrow: string; title: React.ReactNode; sub?: string }) {
  return (
    <div style={{ marginBottom: 36 }}>
      <Eyebrow>{eyebrow}</Eyebrow>
      <h2 style={{ fontFamily: 'var(--fd)', fontSize: 24, fontWeight: 300, color: DK, margin: '4px 0 10px', lineHeight: 1.3 }}>
        {title}
      </h2>
      {sub && (
        <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: NL, margin: 0, maxWidth: 680 }}>{sub}</p>
      )}
    </div>
  );
}

// ── View toggle ───────────────────────────────────────────────────────────────

function ViewToggle({ view, onChange }: { view: View; onChange: (v: View) => void }) {
  return (
    <div style={{ display: 'flex', gap: 8, marginTop: 28 }}>
      {(['business', 'engineering'] as const).map(v => {
        const active = view === v;
        return (
          <button
            key={v}
            onClick={() => onChange(v)}
            style={{
              fontFamily: 'var(--fb)',
              fontSize: 10,
              fontWeight: 600,
              letterSpacing: '1.5px',
              textTransform: 'uppercase',
              padding: '10px 28px',
              background: active ? G : 'transparent',
              color: active ? WH : 'rgba(255,255,255,0.5)',
              border: `1px solid ${active ? G : 'rgba(255,255,255,0.2)'}`,
              borderRadius: 6,
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
          >
            {v === 'business' ? 'Business View' : 'Engineering View'}
          </button>
        );
      })}
    </div>
  );
}

// ── BUSINESS VIEW components ──────────────────────────────────────────────────

function StatBox({ value, label, sub }: { value: string; label: string; sub: string }) {
  return (
    <div style={{
      flex: '1 1 180px',
      padding: '24px 20px',
      background: `linear-gradient(135deg, ${N}0D, ${N}06)`,
      border: `1px solid ${NB}`,
      borderLeft: `3px solid ${G}`,
      borderRadius: 10,
    }}>
      <div style={{ fontFamily: 'var(--fd)', fontSize: 36, fontWeight: 300, color: DK, lineHeight: 1 }}>{value}</div>
      <div style={{ fontFamily: 'var(--fb)', fontSize: 12, fontWeight: 700, color: DK, marginTop: 6 }}>{label}</div>
      <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: NL, marginTop: 4 }}>{sub}</div>
    </div>
  );
}

function FlowDiagram() {
  const steps: Array<{ icon: string; label: string; sub: string; accent: string }> = [
    { icon: '◈', label: 'Digital Signals',   sub: 'Calendar · Slack\nJira · GitHub metadata', accent: NM },
    { icon: '⟡', label: 'Stream Ingestion',  sub: 'Kafka event topics\nAvro schema validated',  accent: NM },
    { icon: '⊞', label: 'ETL Enrichment',    sub: 'Airflow DAGs\nDaily aggregation',             accent: NM },
    { icon: '◎', label: 'ML Scoring',        sub: 'Isolation Forest\nLSTM trend model',          accent: G  },
    { icon: '▲', label: 'AFS Score',         sub: 'Attention Fragmentation\nScore 0 – 100',       accent: G  },
    { icon: '✦', label: 'HR Action',         sub: 'Alerts · Interventions\nCompliance audit',    accent: GN },
  ];

  return (
    <div style={{ overflowX: 'auto', paddingBottom: 8 }}>
      <div style={{ display: 'flex', alignItems: 'stretch', gap: 0, minWidth: 760, padding: '4px 0' }}>
        {steps.flatMap((step, i) => [
          <div
            key={step.label}
            style={{
              flex: '1 1 0',
              background: step.accent === GN ? '#EEF9F4' : step.accent === G ? '#FDF5E6' : '#EEF2F8',
              border: `1px solid ${step.accent === GN ? GN + '55' : step.accent === G ? G + '55' : NB}`,
              borderRadius: 10,
              padding: '18px 14px',
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: 22, marginBottom: 10, color: step.accent }}>{step.icon}</div>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 11, fontWeight: 700, color: DK, letterSpacing: '0.5px', marginBottom: 6 }}>
              {step.label}
            </div>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 10, color: NL, lineHeight: 1.6, whiteSpace: 'pre-line' }}>
              {step.sub}
            </div>
          </div>,
          i < steps.length - 1
            ? <div key={`arr-${i}`} style={{ flex: '0 0 26px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: NL, fontSize: 18 }}>→</div>
            : null,
        ])}
      </div>
    </div>
  );
}

function ZoneGuide() {
  const zones = [
    {
      zone: 'Green', afs: '0 – 39', color: GN, bg: '#EEF9F4', border: GN + '55', label: 'Healthy',
      desc: 'The team is operating within sustainable workload limits. Focus time is protected and collaboration patterns are healthy. No action required; continue monitoring.',
    },
    {
      zone: 'Yellow', afs: '40 – 69', color: G, bg: '#FDF5E6', border: G + '55', label: 'Monitor',
      desc: 'Early signs of fragmentation. HR should schedule a check-in and review sprint commitments. Left unaddressed for 2–3 weeks, Yellow teams reliably transition into Red.',
    },
    {
      zone: 'Red', afs: '70 – 100', color: RD, bg: '#FEF2F4', border: RD + '55', label: 'Intervene',
      desc: 'High burnout risk. The platform fires an automated alert with intervention suggestions. HR should act within 48 hours. Three or more consecutive Red days triggers escalation.',
    },
  ];
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 16 }}>
      {zones.map(z => (
        <div key={z.zone} style={{ background: z.bg, border: `1px solid ${z.border}`, borderRadius: 10, padding: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
            <div style={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: z.color, flexShrink: 0 }} />
            <span style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', color: z.color }}>{z.zone}</span>
            <span style={{ fontFamily: 'var(--fb)', fontSize: 10, color: NL, marginLeft: 'auto' }}>AFS {z.afs}</span>
          </div>
          <div style={{ fontFamily: 'var(--fd)', fontSize: 20, fontWeight: 300, color: DK, marginBottom: 10 }}>{z.label}</div>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: NL, lineHeight: 1.65 }}>{z.desc}</div>
        </div>
      ))}
    </div>
  );
}

function CapabilityCards() {
  const cards = [
    {
      title: 'Team Resilience Dashboard',
      sub: 'Org-wide visibility',
      accent: N,
      desc: 'A real-time view of every team\'s Attention Fragmentation Score, organized by department and resilience zone. The dashboard surfaces current AFS, 30-day trends, and 7-day sparklines — giving HR a single screen to identify which teams need attention, without reading through individual activity reports.',
    },
    {
      title: 'Alert Feed',
      sub: 'Proactive intervention triggers',
      accent: OR,
      desc: 'When a team enters the Red Zone for three or more consecutive days, the system fires an alert with the specific signals that triggered it and a set of tailored interventions — not generic advice, but actions calibrated to the team\'s actual stress pattern (calendar overload, after-hours activity, sprint pressure).',
    },
    {
      title: 'Audit Log',
      sub: 'Compliance & accountability',
      accent: G,
      desc: 'Every dashboard read, alert acknowledgment, and intervention decision is logged with actor identity and timestamp. Available exclusively to HR Admins, the audit log provides a verifiable, immutable record of how team resilience data was accessed — critical for labor compliance and internal governance.',
    },
  ];
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 20 }}>
      {cards.map(c => (
        <div key={c.title} style={{ border: `1px solid ${NB}`, borderTop: `3px solid ${c.accent}`, borderRadius: 10, padding: 24, background: WH }}>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', color: NL, marginBottom: 6 }}>{c.sub}</div>
          <div style={{ fontFamily: 'var(--fd)', fontSize: 18, fontWeight: 300, color: DK, marginBottom: 12 }}>{c.title}</div>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: NL, lineHeight: 1.7 }}>{c.desc}</div>
        </div>
      ))}
    </div>
  );
}

function ComplianceRules() {
  const rules = [
    { num: '01', title: 'No Content Capture', desc: 'Only metadata is collected — event timestamps, durations, and counts. Message bodies, document contents, and video streams are never ingested or stored. The source connectors are engineered to extract timing signals only.' },
    { num: '02', title: 'Team-Level Aggregation Only', desc: 'Individual user data is aggregated into team units before being written to the warehouse. No individual-level burnout scores are computed, stored, or shown to any user — including HR Admins. Privacy is enforced at the data model level.' },
    { num: '03', title: 'Consent-First Collection', desc: 'All data collection requires explicit opt-in configured at the workspace or org level by an administrator. Employees can verify what metadata is collected at any time, and the organization can disable collection for any team.' },
    { num: '04', title: 'Data Minimization', desc: 'Raw event records are retained for ≤7 days on Kafka topics. Aggregated team features are retained for ≤90 days in the warehouse. Older records are automatically purged by TTL policies, not manual processes.' },
    { num: '05', title: 'Audit Logging', desc: 'Every API call that reads resilience data is logged with actor identity, timestamp, and the specific resource accessed. Audit logs are append-only and available exclusively to HR Admins — providing a verifiable chain of custody for sensitive team data.' },
  ];
  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      {rules.map(r => (
        <div key={r.num} style={{ display: 'flex', gap: 24, padding: '22px 0', borderBottom: `1px solid ${NB}` }}>
          <div style={{ flex: '0 0 auto', fontFamily: 'var(--fd)', fontSize: 28, fontWeight: 300, color: G, lineHeight: 1, paddingTop: 2 }}>{r.num}</div>
          <div>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 13, fontWeight: 700, color: DK, marginBottom: 6 }}>{r.title}</div>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 13, color: NL, lineHeight: 1.65, maxWidth: 700 }}>{r.desc}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

function AfsFeatureGrid() {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12, marginBottom: 36 }}>
      {[
        { abbr: 'CDS', name: 'Calendar Density Score', weight: '30%', desc: 'Proportion of working hours occupied by meetings. Sustained CDS > 0.65 indicates insufficient protected focus time.' },
        { abbr: 'AHAI', name: 'After-Hours Activity Index', weight: '30%', desc: 'Messaging and commit activity outside core hours, normalized by team size and timezone spread.' },
        { abbr: 'CSC', name: 'Context Switch Count', weight: '20%', desc: 'Number of cross-project, cross-channel context transitions per day — a proxy for cognitive interrupt frequency.' },
        { abbr: 'SHI', name: 'Sprint Health Index', weight: '20%', desc: 'Inverted delivery metric: story points completed vs. committed, PR cycle time, and incident frequency. Higher SHI = healthier delivery.' },
      ].map(f => (
        <div key={f.abbr} style={{ padding: '16px 18px', background: WH, border: `1px solid ${NB}`, borderRadius: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
            <span style={{ fontFamily: 'var(--fb)', fontSize: 14, fontWeight: 700, color: DK }}>{f.abbr}</span>
            <span style={{ fontFamily: 'var(--fb)', fontSize: 10, color: G, fontWeight: 700 }}>{f.weight}</span>
          </div>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: NM, marginBottom: 8 }}>{f.name}</div>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: NL, lineHeight: 1.6 }}>{f.desc}</div>
        </div>
      ))}
    </div>
  );
}

function BusinessView() {
  return (
    <>
      {/* Problem */}
      <Sec>
        <SH
          eyebrow="Business Context"
          title="The cost of undetected burnout."
          sub="Burnout is expensive, predictable, and largely preventable — if you have the right signals early enough. Most organizations discover a burnout problem only when an employee resigns, requests medical leave, or shows a sharp drop in output. By that point, the cost is already incurred."
        />
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 32 }}>
          <StatBox value="$322B"  label="Annual productivity loss"           sub="Gallup — global cost attributable to employee burnout" />
          <StatBox value="3–6×"   label="Salary cost to replace talent"       sub="Hiring, onboarding, and full ramp-up combined" />
          <StatBox value="4–6 wk" label="Typical HR detection lag"            sub="Without tooling, patterns surface weeks after onset" />
          <StatBox value="67%"    label="Burnout precedes voluntary attrition" sub="Of exits were preceded by measurable exhaustion signals" />
        </div>
        <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: NL, lineHeight: 1.75, maxWidth: 780 }}>
          The challenge is not identifying burned-out employees retroactively — it is detecting the behavioral precursors weeks before attrition or medical leave occurs. Teams heading toward burnout emit consistent and measurable digital signals: back-to-back calendar blocks, after-hours messaging activity, high context-switching frequency, and declining sprint delivery rates. These signals exist in systems your organization already owns. The Burnout &amp; Cognitive Load Guardrail makes them visible to the people responsible for acting on them.
        </p>
      </Sec>

      {/* How it works */}
      <Sec tinted>
        <SH
          eyebrow="Solution Overview"
          title={<>Real-time signals. <em style={{ fontStyle: 'italic' }}>Early warnings.</em></>}
          sub="The platform passively collects collaboration metadata from the tools your teams already use — no surveys, no self-reporting, no behavior change required from employees or managers."
        />
        <FlowDiagram />
        <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: NL, lineHeight: 1.75, maxWidth: 780, margin: '28px 0 0' }}>
          Data flows from calendar, messaging, project management, and version control tools into a streaming pipeline. The machine learning layer computes a single composite score — the <strong style={{ color: DK }}>Attention Fragmentation Score (AFS)</strong> — for each Team Unit, updated daily. HR teams interact exclusively with aggregated, team-level data. No individual scores are surfaced at any point in the pipeline.
        </p>
      </Sec>

      {/* Capabilities */}
      <Sec>
        <SH
          eyebrow="Platform Capabilities"
          title={<>Three tools for <em style={{ fontStyle: 'italic' }}>HR teams.</em></>}
          sub="Each capability is designed around a specific HR workflow: monitoring, responding, and documenting. Together they cover the full lifecycle from early detection to recorded intervention."
        />
        <CapabilityCards />
      </Sec>

      {/* AFS + zones */}
      <Sec tinted>
        <SH
          eyebrow="Scoring Framework"
          title="The Attention Fragmentation Score."
          sub="AFS is a composite index (0–100) derived from four measurable collaboration signals. Higher scores indicate more fragmented work patterns and greater burnout risk. The score is computed daily per Team Unit — never per individual employee."
        />
        <AfsFeatureGrid />
        <ZoneGuide />
        <div style={{ marginTop: 20, padding: '14px 18px', background: WH, border: `1px solid ${NB}`, borderRadius: 8 }}>
          <span style={{ fontFamily: 'Courier New, monospace', fontSize: 12, color: NM }}>
            <strong style={{ color: DK }}>AFS = </strong>
            (0.30 × CDS + 0.30 × AHAI + 0.20 × CSC + 0.20 × (1 − SHI)) × 100
          </span>
        </div>
      </Sec>

      {/* Compliance */}
      <Sec>
        <SH
          eyebrow="Privacy & Compliance"
          title={<>Built for <em style={{ fontStyle: 'italic' }}>trust.</em></>}
          sub="Every design decision in this platform was made with employee privacy as a primary constraint, not an afterthought. The following rules are enforced at the architecture level — not just in policy documents."
        />
        <ComplianceRules />
      </Sec>
    </>
  );
}

// ── ENGINEERING VIEW components ───────────────────────────────────────────────

function ArchSvg() {
  const layers = [
    { num: '01', label: 'DATA SOURCES',             tech: 'Google Calendar API  ·  Slack Events API  ·  Jira REST API  ·  GitHub Webhooks',                      bg: '#EEF2F8', stroke: N,  tc: DK          },
    { num: '02', label: 'EVENT STREAMING',           tech: 'Apache Kafka (Confluent Cloud / self-hosted)  ·  Avro Schema Registry',                               bg: '#EEF2F8', stroke: NM, tc: DK          },
    { num: '03', label: 'ORCHESTRATION & STORAGE',  tech: 'Apache Airflow (MWAA / Astronomer)  ·  Snowflake / BigQuery',                                          bg: '#EEF2F8', stroke: NM, tc: DK          },
    { num: '04', label: 'ML PIPELINE',               tech: 'scikit-learn Isolation Forest  ·  PyTorch LSTM  →  AFS Score (0 – 100)',                              bg: '#FDF5E6', stroke: G,  tc: '#7A5C10'   },
    { num: '05', label: 'INFERENCE & BACKEND API',  tech: 'FastAPI + Uvicorn  ·  OAuth 2.0 (Okta / Auth0)  ·  Pydantic v2  ·  Role-Based Middleware',             bg: '#EEF2F8', stroke: NM, tc: DK          },
    { num: '06', label: 'DASHBOARD',                 tech: 'React 18  ·  TypeScript (strict)  ·  Recharts  ·  Zustand  ·  React Query',                           bg: '#EEF9F4', stroke: GN, tc: '#1A5C3A'   },
  ];

  const BOX_H = 58;
  const GAP   = 28;
  const totalH = layers.length * BOX_H + (layers.length - 1) * GAP + 40;

  return (
    <svg width="100%" viewBox={`0 0 720 ${totalH}`} style={{ display: 'block' }} role="img" aria-label="System architecture — six-layer stack diagram">
      <defs>
        <marker id="arch-arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
          <polygon points="0 0, 8 3, 0 6" fill={NL} />
        </marker>
      </defs>
      {layers.map((layer, i) => {
        const y = 20 + i * (BOX_H + GAP);
        return (
          <Fragment key={layer.num}>
            <rect x="10" y={y} width="700" height={BOX_H} rx="8" fill={layer.bg} stroke={layer.stroke} strokeWidth="1.5" />
            <text x="26" y={y + 17} fontFamily="'Plus Jakarta Sans', sans-serif" fontSize="8" fontWeight="700" letterSpacing="2" fill={NL}>{layer.num} · {layer.label}</text>
            <text x="26" y={y + 40} fontFamily="'Plus Jakarta Sans', sans-serif" fontSize="13" fontWeight="600" fill={layer.tc}>{layer.tech}</text>
            {i < layers.length - 1 && (
              <line x1="360" y1={y + BOX_H} x2="360" y2={y + BOX_H + GAP - 8} stroke={NL} strokeWidth="1.5" markerEnd="url(#arch-arrow)" />
            )}
          </Fragment>
        );
      })}
    </svg>
  );
}

function MlSvg() {
  const features = [
    { label: 'Calendar Density Score', sub: 'CDS · weight 30%', y: 14  },
    { label: 'After-Hours Activity',   sub: 'AHAI · weight 30%', y: 74  },
    { label: 'Context Switch Count',   sub: 'CSC · weight 20%',  y: 134 },
    { label: 'Sprint Health Index',    sub: 'SHI · weight 20%',  y: 194 },
  ];

  return (
    <svg width="100%" viewBox="0 0 720 252" style={{ display: 'block' }} role="img" aria-label="ML pipeline — features to AFS score">
      <defs>
        <marker id="ml-arr"   markerWidth="7" markerHeight="5" refX="7" refY="2.5" orient="auto">
          <polygon points="0 0, 7 2.5, 0 5" fill={NL} />
        </marker>
        <marker id="ml-arr-g" markerWidth="7" markerHeight="5" refX="7" refY="2.5" orient="auto">
          <polygon points="0 0, 7 2.5, 0 5" fill={G} />
        </marker>
      </defs>

      {/* Feature boxes */}
      {features.map(f => (
        <Fragment key={f.label}>
          <rect x="10" y={f.y} width="190" height="42" rx="6" fill="#EEF2F8" stroke={N} strokeWidth="1" />
          <text x="21" y={f.y + 17} fontFamily="'Plus Jakarta Sans', sans-serif" fontSize="11" fontWeight="600" fill={DK}>{f.label}</text>
          <text x="21" y={f.y + 33} fontFamily="'Plus Jakarta Sans', sans-serif" fontSize="9" fill={NL}>{f.sub}</text>
        </Fragment>
      ))}

      {/* Lines → Isolation Forest */}
      <line x1="200" y1="35"  x2="278" y2="84"  stroke={NL} strokeWidth="1.2" markerEnd="url(#ml-arr)" />
      <line x1="200" y1="95"  x2="278" y2="97"  stroke={NL} strokeWidth="1.2" markerEnd="url(#ml-arr)" />
      <line x1="200" y1="155" x2="278" y2="110" stroke={NL} strokeWidth="1.2" markerEnd="url(#ml-arr)" />

      {/* SHI → LSTM */}
      <line x1="200" y1="215" x2="278" y2="188" stroke={NL} strokeWidth="1.2" markerEnd="url(#ml-arr)" />

      {/* Isolation Forest */}
      <rect x="278" y="60" width="168" height="72" rx="6" fill="#FDF5E6" stroke={G} strokeWidth="1.5" />
      <text x="362" y="89"  fontFamily="'Plus Jakarta Sans', sans-serif" fontSize="12" fontWeight="700" fill="#7A5C10" textAnchor="middle">Isolation Forest</text>
      <text x="362" y="107" fontFamily="'Plus Jakarta Sans', sans-serif" fontSize="10" fill="#A07830" textAnchor="middle">Unsupervised anomaly</text>
      <text x="362" y="122" fontFamily="'Plus Jakarta Sans', sans-serif" fontSize="10" fill="#A07830" textAnchor="middle">detection per feature</text>

      {/* LSTM */}
      <rect x="278" y="160" width="168" height="56" rx="6" fill="#FDF5E6" stroke={G} strokeWidth="1.5" />
      <text x="362" y="185" fontFamily="'Plus Jakarta Sans', sans-serif" fontSize="12" fontWeight="700" fill="#7A5C10" textAnchor="middle">LSTM</text>
      <text x="362" y="204" fontFamily="'Plus Jakarta Sans', sans-serif" fontSize="10" fill="#A07830" textAnchor="middle">30-day temporal trend</text>

      {/* Lines → AFS */}
      <line x1="446" y1="96"  x2="514" y2="112" stroke={G} strokeWidth="1.5" markerEnd="url(#ml-arr-g)" />
      <line x1="446" y1="188" x2="514" y2="130" stroke={G} strokeWidth="1.5" markerEnd="url(#ml-arr-g)" />

      {/* AFS Score output */}
      <rect x="514" y="84" width="176" height="76" rx="6" fill="#EEF9F4" stroke={GN} strokeWidth="1.5" />
      <text x="602" y="112" fontFamily="'Plus Jakarta Sans', sans-serif" fontSize="14" fontWeight="700" fill={DK}  textAnchor="middle">AFS Score</text>
      <text x="602" y="130" fontFamily="'Plus Jakarta Sans', sans-serif" fontSize="11" fill={NL}  textAnchor="middle">Range: 0 – 100</text>
      <text x="602" y="148" fontFamily="'Plus Jakarta Sans', sans-serif" fontSize="9"  fill={NL}  textAnchor="middle">Attention Fragmentation Index</text>
    </svg>
  );
}

function KafkaFlow() {
  const items = [
    { label: 'Source Connector', sub: 'Polls source API\nevery 15 min',       bg: '#EEF2F8', stroke: N  },
    { label: 'Kafka Topic',      sub: 'Avro-encoded events\nRetained 7 days',  bg: '#FDF5E6', stroke: G  },
    { label: 'Stream Consumer',  sub: 'Reads offsets\nidempotently',           bg: '#EEF2F8', stroke: NM },
    { label: 'Airflow DAG',      sub: 'Aggregates to\nTeam Unit features',     bg: '#EEF2F8', stroke: NM },
    { label: 'Data Warehouse',   sub: 'Columnar storage\nwith TTL policy',     bg: '#EEF9F4', stroke: GN },
  ];
  return (
    <div style={{ overflowX: 'auto', paddingBottom: 8 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 0, minWidth: 640 }}>
        {items.flatMap((item, i) => [
          <div key={item.label} style={{ flex: '1 1 0', background: item.bg, border: `1px solid ${item.stroke}44`, borderRadius: 8, padding: '14px 12px', textAlign: 'center' }}>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 11, fontWeight: 700, color: DK, marginBottom: 6 }}>{item.label}</div>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 10, color: NL, lineHeight: 1.6, whiteSpace: 'pre-line' }}>{item.sub}</div>
          </div>,
          i < items.length - 1
            ? <div key={`karr-${i}`} style={{ flex: '0 0 22px', textAlign: 'center', color: NL, fontSize: 16 }}>→</div>
            : null,
        ])}
      </div>
    </div>
  );
}

function TechTable() {
  const rows = [
    { layer: 'Event Streaming',    tech: 'Apache Kafka + Avro',                   why: 'Ordered, replayable event log with schema enforcement. Avro prevents malformed messages from entering the pipeline; replay enables ML retraining without re-querying source APIs.' },
    { layer: 'Orchestration',      tech: 'Apache Airflow',                         why: 'DAG-based ETL with retry semantics and idempotency. Visual pipeline monitoring; MWAA or Astronomer for managed cloud deployment with zero infrastructure overhead.' },
    { layer: 'Data Warehouse',     tech: 'Snowflake / BigQuery',                   why: 'Columnar storage optimized for time-series team features. Automated TTL partitions enforce the 7-day raw and 90-day aggregate retention rules without manual cleanup jobs.' },
    { layer: 'Anomaly Detection',  tech: 'Isolation Forest (scikit-learn)',         why: 'Unsupervised — no labeled burnout data required. Identifies statistically anomalous feature combinations for each team without a positive training set.' },
    { layer: 'Trend Detection',    tech: 'LSTM (PyTorch)',                          why: 'Captures temporal dependencies in 30-day rolling windows. Distinguishes sustained deterioration from transient spikes, reducing false-positive alert rate for HR.' },
    { layer: 'Inference API',      tech: 'FastAPI + Uvicorn',                       why: 'Async-first with sub-millisecond routing overhead. Auto-generates OpenAPI spec; Pydantic v2 validation on every request and response body.' },
    { layer: 'Authentication',     tech: 'OAuth 2.0 (Okta / Auth0)',               why: 'SSO integration with enterprise identity providers. Role claims embedded in JWT; enforced server-side on every endpoint — client-side guards are UX convenience only.' },
    { layer: 'Frontend',           tech: 'React 18 + TypeScript (strict)',          why: 'Functional component model with hooks suits real-time dashboard patterns. Strict mode with exactOptionalPropertyTypes prevents silent runtime type errors.' },
    { layer: 'Charts',             tech: 'Recharts',                                why: 'SVG-based, accessible, composable. Integrates directly with React state for real-time data binding without imperative D3 mutations.' },
    { layer: 'State Management',   tech: 'Zustand + React Query',                  why: 'Zustand for auth and global UI state (minimal boilerplate). React Query for server state with stale-while-revalidate caching and automatic background refresh.' },
    { layer: 'CI / CD',            tech: 'GitHub Actions + Docker + Terraform',    why: 'Reproducible dev/prod environments via containers. IaC provides audit trails for infrastructure changes. CI gates enforce ruff, mypy (strict), and tsc on every pull request.' },
  ];
  return (
    <div style={{ overflowX: 'auto', borderRadius: 10, boxShadow: '0 1px 4px rgba(0,51,102,0.08)' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', backgroundColor: WH, minWidth: 620 }}>
        <thead>
          <tr style={{ backgroundColor: N }}>
            {['Layer', 'Technology', 'Design Justification'].map(h => (
              <th key={h} style={{ padding: '12px 16px', fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 500, letterSpacing: '2px', textTransform: 'uppercase', color: WH, textAlign: 'left', whiteSpace: 'nowrap' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={row.layer} style={{ backgroundColor: i % 2 === 0 ? WH : '#F8F9FC' }}>
              <td style={{ padding: '12px 16px', fontFamily: 'var(--fb)', fontSize: 12, fontWeight: 700, color: DK, borderBottom: `1px solid ${NB}`, whiteSpace: 'nowrap', verticalAlign: 'top' }}>{row.layer}</td>
              <td style={{ padding: '12px 16px', fontFamily: 'Courier New, monospace', fontSize: 11, color: NM, borderBottom: `1px solid ${NB}`, whiteSpace: 'nowrap', verticalAlign: 'top' }}>{row.tech}</td>
              <td style={{ padding: '12px 16px', fontFamily: 'var(--fb)', fontSize: 12, color: NL, borderBottom: `1px solid ${NB}`, lineHeight: 1.65, verticalAlign: 'top' }}>{row.why}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RbacDiagram() {
  const roles = [
    {
      role: 'HR Admin',
      color: N,
      bg: '#EEF2F8',
      desc: 'Full platform access. Responsible for acting on alerts and maintaining compliance accountability.',
      permissions: ['Dashboard — full org view', 'Alert Feed — all teams', 'Team Drill-Down — any team', 'Audit Log — read', 'Interventions — apply & dismiss'],
    },
    {
      role: 'Viewer',
      color: NM,
      bg: '#EEF2F8',
      desc: 'Read-only access to resilience data. Suitable for senior leadership or People Analytics roles.',
      permissions: ['Dashboard — full org view', 'Alert Feed — all teams', 'Team Drill-Down — any team'],
    },
    {
      role: 'Team Manager',
      color: OR,
      bg: '#FEF4EE',
      desc: 'Scoped access limited to their own team. Cannot view peer teams or org-wide aggregates.',
      permissions: ['Team Drill-Down — own team only'],
    },
  ];
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
      {roles.map(r => (
        <div key={r.role} style={{ background: r.bg, border: `1px solid ${r.color}44`, borderTop: `3px solid ${r.color}`, borderRadius: 10, padding: 20 }}>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 13, fontWeight: 700, color: r.color, marginBottom: 6 }}>{r.role}</div>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: NL, lineHeight: 1.55, marginBottom: 14 }}>{r.desc}</div>
          <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 7 }}>
            {r.permissions.map(p => (
              <li key={p} style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                <span style={{ color: GN, fontSize: 12, marginTop: 1, flexShrink: 0 }}>✓</span>
                <span style={{ fontFamily: 'var(--fb)', fontSize: 12, color: DK, lineHeight: 1.4 }}>{p}</span>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

function EngineeringView() {
  return (
    <>
      {/* Architecture */}
      <Sec>
        <SH
          eyebrow="System Architecture"
          title={<>Six integrated <em style={{ fontStyle: 'italic' }}>layers.</em></>}
          sub="The platform decomposes into six independently deployable layers, each with a clear boundary and single responsibility. Data flows top-to-bottom; the ML layer is the value-generating core. The dashboard layer consumes only the API — it has no direct access to the warehouse or the event stream."
        />
        <ArchSvg />
      </Sec>

      {/* Tech Stack */}
      <Sec tinted>
        <SH
          eyebrow="Technology Stack"
          title={<>Chosen for <em style={{ fontStyle: 'italic' }}>reliability and scale.</em></>}
          sub="Every technology choice was evaluated against three criteria: operational maturity, fit for the streaming and ML workload, and alignment with data privacy constraints. Where multiple options were viable, the choice with the strongest managed-service ecosystem was preferred to minimize operational burden."
        />
        <TechTable />
      </Sec>

      {/* Kafka */}
      <Sec>
        <SH
          eyebrow="Ingestion Layer"
          title={<>Kafka: ordered, replayable, <em style={{ fontStyle: 'italic' }}>fault-tolerant.</em></>}
          sub="Apache Kafka is the backbone of the ingestion layer. Every collaboration metadata event enters the system as an Avro-encoded message on a dedicated topic, providing strict ordering, schema enforcement, and the ability to replay the full event history for ML retraining."
        />
        <KafkaFlow />
        <div style={HR} />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
          {[
            { title: 'Schema Registry', desc: 'Every event type has an Avro schema registered before any producer is allowed to publish. Consumers cannot silently receive schema-broken messages — evolution is explicit and versioned.' },
            { title: 'Replay Capability', desc: 'Seven-day retention on raw topics means the ML pipeline can be retrained or recalibrated by replaying historical signals without re-querying source APIs or breaking consent boundaries.' },
            { title: 'Idempotent Consumers', desc: 'Airflow DAGs track committed Kafka partition offsets. A DAG re-run will not double-count events — a required property for the data minimization and audit compliance rules.' },
          ].map(c => (
            <div key={c.title} style={{ padding: '18px 16px', background: '#EEF2F8', border: `1px solid ${NB}`, borderRadius: 8 }}>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 12, fontWeight: 700, color: DK, marginBottom: 6 }}>{c.title}</div>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: NL, lineHeight: 1.65 }}>{c.desc}</div>
            </div>
          ))}
        </div>
      </Sec>

      {/* ML Pipeline */}
      <Sec tinted>
        <SH
          eyebrow="Machine Learning Pipeline"
          title={<>Two models. <em style={{ fontStyle: 'italic' }}>One score.</em></>}
          sub="The AFS is computed by combining cross-sectional anomaly signals from an Isolation Forest with temporal trend signals from an LSTM. The two outputs are merged using a fixed-weight formula, producing a single daily score per Team Unit."
        />
        <MlSvg />
        <div style={HR} />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 20 }}>
          <div style={{ padding: '20px 18px', background: '#FDF5E6', border: `1px solid ${G}44`, borderRadius: 8 }}>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 12, fontWeight: 700, color: '#7A5C10', marginBottom: 8 }}>Why Isolation Forest?</div>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: NL, lineHeight: 1.7 }}>
              Burnout-state data is not labeled in most organizations — there is no dataset of "confirmed burned-out teams." Isolation Forest is an unsupervised algorithm that scores anomalies without a positive training set. It identifies feature combinations that are statistically unusual <em>for that specific team</em>, relative to its own history, regardless of what "normal burnout" looks like globally. This makes it robust to differences in team size, timezone, and work culture.
            </div>
          </div>
          <div style={{ padding: '20px 18px', background: '#FDF5E6', border: `1px solid ${G}44`, borderRadius: 8 }}>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 12, fontWeight: 700, color: '#7A5C10', marginBottom: 8 }}>Why LSTM?</div>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: NL, lineHeight: 1.7 }}>
              A single-day anomaly may be noise — a project deadline, a company all-hands, a sprint release. LSTM captures temporal dependencies in 30-day rolling windows, distinguishing <em>sustained deterioration</em> (which carries high burnout risk) from <em>transient spikes</em> (which do not). This is the primary mechanism for reducing false-positive alert rate and preventing HR alert fatigue.
            </div>
          </div>
        </div>
        <div style={{ marginTop: 16, padding: '14px 18px', background: WH, border: `1px solid ${NB}`, borderRadius: 8 }}>
          <span style={{ fontFamily: 'Courier New, monospace', fontSize: 12, color: NM }}>
            <strong style={{ color: DK }}>AFS = </strong>
            (0.30 × CDS + 0.30 × AHAI + 0.20 × CSC + 0.20 × (1 − SHI)) × 100
          </span>
        </div>
      </Sec>

      {/* Security & RBAC */}
      <Sec>
        <SH
          eyebrow="Security & Access Control"
          title={<>Role-based access, <em style={{ fontStyle: 'italic' }}>enforced server-side.</em></>}
          sub="Authentication is delegated to OAuth 2.0 via enterprise SSO (Okta or Auth0). Role claims are embedded in JWT tokens and verified by FastAPI middleware on every request. The frontend enforces roles as a UX convenience; the API is the authoritative access gate."
        />
        <RbacDiagram />
        <div style={HR} />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
          {[
            { title: 'JWT Role Claims', desc: 'The user\'s role (hr_admin, viewer, team_manager) is embedded in the JWT payload at SSO login. FastAPI middleware reads and validates the claim before executing any route handler — no database lookup required per request.' },
            { title: 'Audit Middleware', desc: 'A dedicated FastAPI middleware intercepts all resilience data reads and writes an audit log entry (actor identity, timestamp, endpoint, resource ID) to an append-only table. The log cannot be modified by any API consumer.' },
            { title: 'No Individual IDs in API', desc: 'API responses never include individual employee identifiers. All team-level aggregates use team_id as the primary key. User identities in the audit log refer only to HR actors, not to employees being monitored.' },
          ].map(c => (
            <div key={c.title} style={{ padding: '18px 16px', background: '#F8F9FC', border: `1px solid ${NB}`, borderRadius: 8 }}>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 12, fontWeight: 700, color: DK, marginBottom: 6 }}>{c.title}</div>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: NL, lineHeight: 1.65 }}>{c.desc}</div>
            </div>
          ))}
        </div>
      </Sec>
    </>
  );
}

// ── Page root ─────────────────────────────────────────────────────────────────

export function InfoPage() {
  const [view, setView] = useState<View>('business');

  return (
    <main>
      <section
        className="hero-dark"
        aria-labelledby="info-title"
        style={{ padding: '56px 48px 48px' }}
      >
        <div style={{ maxWidth: MAX_W, margin: '0 auto' }}>
          <Eyebrow>Platform Documentation</Eyebrow>
          <h1
            id="info-title"
            style={{ fontFamily: 'var(--fd)', fontSize: 36, fontWeight: 300, color: WH, margin: '8px 0 12px', lineHeight: 1.2 }}
          >
            Burnout &amp; Cognitive Load{' '}
            <em style={{ fontStyle: 'italic', color: 'var(--gold-light)' }}>Guardrail.</em>
          </h1>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'rgba(255,255,255,0.5)', margin: 0, maxWidth: 560 }}>
            A reference for the people who use this platform and the engineers who build it.
            Choose a lens below to explore what matters most to you.
          </p>
          <ViewToggle view={view} onChange={setView} />
        </div>
      </section>

      {view === 'business' ? <BusinessView /> : <EngineeringView />}
    </main>
  );
}
