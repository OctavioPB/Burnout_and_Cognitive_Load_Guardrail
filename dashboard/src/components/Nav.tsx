/** Sticky navigation bar — OPB monogram + page links + logout. */

import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';

const ROLE_LABEL: Record<string, string> = {
  hr_admin:     'HR Admin',
  team_manager: 'Team Manager',
  viewer:       'Viewer',
};

interface NavLink {
  path: string;
  label: string;
  roles?: string[];
}

const NAV_LINKS: NavLink[] = [
  { path: '/dashboard', label: 'Dashboard' },
  { path: '/alerts',    label: 'Alert Feed' },
  { path: '/audit',     label: 'Audit Log',  roles: ['hr_admin'] },
  { path: '/info',      label: 'About' },
];

export function Nav() {
  const navigate   = useNavigate();
  const { pathname } = useLocation();
  const { user, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const visibleLinks = NAV_LINKS.filter(
    l => !l.roles || (user && l.roles.includes(user.role)),
  );

  return (
    <nav
      aria-label="Main navigation"
      style={{
        backgroundColor: 'rgba(0,51,102,0.97)',
        backdropFilter: 'blur(12px)',
        height: 52,
        position: 'sticky',
        top: 0,
        zIndex: 100,
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        padding: '0 40px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}
    >
      {/* Left — OPB monogram */}
      <button
        onClick={() => navigate('/dashboard')}
        aria-label="Go to dashboard"
        style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, display: 'flex', alignItems: 'center', gap: 14 }}
      >
        <span>
          <span style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 20, fontWeight: 300, color: '#ffffff' }}>O</span>
          <em style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 20, fontWeight: 300, fontStyle: 'italic', color: 'var(--gold-light)' }}>PB</em>
        </span>
        <span style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '3px', textTransform: 'uppercase', color: 'rgba(255,255,255,0.35)' }}>
          Resilience Dashboard
        </span>
      </button>

      {/* Right cluster — page links + role + logout */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        {visibleLinks.map(link => {
          const isActive = pathname.startsWith(link.path);
          return (
            <button
              key={link.path}
              onClick={() => navigate(link.path)}
              aria-current={isActive ? 'page' : undefined}
              style={{
                background: isActive ? 'rgba(201,168,76,0.12)' : 'none',
                border: 'none',
                color: isActive ? 'var(--gold-light)' : 'rgba(255,255,255,0.45)',
                cursor: 'pointer',
                fontFamily: 'var(--fb)',
                fontSize: 9,
                letterSpacing: '2px',
                textTransform: 'uppercase',
                padding: '5px 8px',
                borderRadius: 6,
                transition: 'color 0.15s',
              }}
            >
              {link.label}
            </button>
          );
        })}

        {user && (
          <span
            style={{
              fontFamily: 'var(--fb)',
              fontSize: 9,
              letterSpacing: '2px',
              textTransform: 'uppercase',
              color: 'rgba(255,255,255,0.3)',
              marginLeft: 12,
              marginRight: 4,
            }}
          >
            {ROLE_LABEL[user.role] ?? user.role}
          </span>
        )}

        <button
          onClick={handleLogout}
          aria-label="Log out"
          style={{
            background: 'none',
            border: '1px solid rgba(255,255,255,0.2)',
            borderRadius: 6,
            color: 'rgba(255,255,255,0.5)',
            cursor: 'pointer',
            fontFamily: 'var(--fb)',
            fontSize: 9,
            letterSpacing: '2px',
            textTransform: 'uppercase',
            padding: '5px 10px',
            marginLeft: 8,
          }}
        >
          Log Out
        </button>
      </div>
    </nav>
  );
}
