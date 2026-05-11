/**
 * Login page — simulates SSO by offering role selection.
 *
 * In production this is replaced by an Okta/Auth0 PKCE redirect.
 * For staging we persist the selected role directly in Zustand.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import type { UserRole, AuthUser } from '../types/domain';

const ROLES: Array<{ role: UserRole; title: string; description: string; team_id?: string }> = [
  {
    role: 'hr_admin',
    title: 'HR Admin',
    description: 'Full access to all teams, alert feed, and audit log.',
  },
  {
    role: 'team_manager',
    title: 'Team Manager',
    description: "Access to your own team's data only (Frontend Engineering).",
    team_id: 'T-01',
  },
  {
    role: 'viewer',
    title: 'Viewer',
    description: 'Read-only access to the dashboard and alert feed.',
  },
];

export function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuthStore();
  const [selected, setSelected] = useState<UserRole>('hr_admin');

  const handleLogin = () => {
    const roleConfig = ROLES.find(r => r.role === selected)!;
    const user: AuthUser = {
      id:    `staging-${selected}`,
      name:  roleConfig.title,
      email: `${selected.replace('_', '.')}@staging.local`,
      role:  selected,
      ...(roleConfig.team_id ? { team_id: roleConfig.team_id } : {}),
    };
    login(user);
    navigate(selected === 'team_manager' && roleConfig.team_id ? `/team/${roleConfig.team_id}` : '/dashboard');
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: 'var(--primary)',
        backgroundImage: `
          linear-gradient(rgba(255,255,255,.025) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255,255,255,.025) 1px, transparent 1px)
        `,
        backgroundSize: '48px 48px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
      }}
    >
      <div
        style={{
          backgroundColor: '#fff',
          borderRadius: 16,
          padding: '48px 44px',
          maxWidth: 440,
          width: '100%',
          boxShadow: '0 8px 40px rgba(0,0,0,0.25)',
        }}
      >
        {/* Monogram */}
        <div style={{ marginBottom: 32, textAlign: 'center' }}>
          <span style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 28, fontWeight: 300, color: 'var(--primary)' }}>O</span>
          <em style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 28, fontWeight: 300, fontStyle: 'italic', color: 'var(--gold)' }}>PB</em>
        </div>

        <h1 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', marginBottom: 6, textAlign: 'center' }}>
          Team <em style={{ fontStyle: 'italic', color: 'var(--primary)' }}>Resilience</em> Dashboard
        </h1>
        <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', textAlign: 'center', marginBottom: 32, lineHeight: 1.6 }}>
          Staging environment — select a role to simulate SSO login.
        </p>

        {/* Role selection */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 28 }} role="radiogroup" aria-label="Select role">
          {ROLES.map(r => (
            <label
              key={r.role}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: 12,
                padding: '14px 16px',
                borderRadius: 10,
                border: `1.5px solid ${selected === r.role ? 'var(--primary)' : 'var(--primary-10)'}`,
                backgroundColor: selected === r.role ? 'var(--primary-10)' : '#fff',
                cursor: 'pointer',
                transition: 'border-color 0.15s',
              }}
            >
              <input
                type="radio"
                name="role"
                value={r.role}
                checked={selected === r.role}
                onChange={() => setSelected(r.role)}
                style={{ marginTop: 2, accentColor: 'var(--primary)' }}
                aria-label={r.title}
              />
              <div>
                <div style={{ fontFamily: 'var(--fb)', fontSize: 13, fontWeight: 600, color: 'var(--dark)', marginBottom: 2 }}>
                  {r.title}
                </div>
                <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', lineHeight: 1.5 }}>
                  {r.description}
                </div>
              </div>
            </label>
          ))}
        </div>

        {/* Gold accent bar */}
        <div style={{ height: 3, backgroundColor: 'var(--gold)', borderRadius: 2, marginBottom: 24 }} />

        <button
          onClick={handleLogin}
          style={{
            width: '100%',
            backgroundColor: 'var(--primary)',
            color: '#fff',
            border: 'none',
            borderRadius: 8,
            padding: '13px 0',
            fontFamily: 'var(--fb)',
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: '2px',
            textTransform: 'uppercase',
            cursor: 'pointer',
            transition: 'background-color 0.15s',
          }}
          onMouseEnter={e => { (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--primary-80)'; }}
          onMouseLeave={e => { (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--primary)'; }}
        >
          Continue as {ROLES.find(r => r.role === selected)?.title}
        </button>
      </div>
    </div>
  );
}
