/**
 * App — route definitions with auth guard and role-based protection.
 *
 * Routes:
 *   /login          → LoginPage (public)
 *   /dashboard      → DashboardHome (hr_admin, viewer)
 *   /team/:teamId   → TeamDrillDown (all roles; team_manager sees only their team)
 *   /alerts         → AlertsPage (hr_admin, viewer)
 *   /audit          → AuditLogPage (hr_admin only)
 *   /               → redirect to /dashboard
 *   *               → redirect to /dashboard
 */

import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from './stores/authStore';
import { Nav } from './components/Nav';
import { Footer } from './components/Footer';
import { ErrorBoundary } from './components/ErrorBoundary';
import { LoginPage } from './pages/LoginPage';
import { DashboardHome } from './pages/DashboardHome';
import { TeamDrillDown } from './pages/TeamDrillDown';
import { AlertsPage } from './pages/AlertsPage';
import { AuditLogPage } from './pages/AuditLogPage';
import { InfoPage } from './pages/InfoPage';
import { HrAdminPage } from './pages/HrAdminPage';

/** Redirects unauthenticated visitors to /login. */
function RequireAuth({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore(s => s.isAuthenticated());
  const location = useLocation();
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return <>{children}</>;
}

/** Shell with sticky nav + footer, wraps authenticated pages. */
function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Nav />
      <div style={{ flex: 1 }}>
        <ErrorBoundary>{children}</ErrorBoundary>
      </div>
      <Footer />
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public */}
        <Route path="/login" element={<LoginPage />} />

        {/* Protected */}
        <Route
          path="/dashboard"
          element={
            <RequireAuth>
              <Shell><DashboardHome /></Shell>
            </RequireAuth>
          }
        />
        <Route
          path="/team/:teamId"
          element={
            <RequireAuth>
              <Shell><TeamDrillDown /></Shell>
            </RequireAuth>
          }
        />
        <Route
          path="/alerts"
          element={
            <RequireAuth>
              <Shell><AlertsPage /></Shell>
            </RequireAuth>
          }
        />
        <Route
          path="/audit"
          element={
            <RequireAuth>
              <Shell><AuditLogPage /></Shell>
            </RequireAuth>
          }
        />
        <Route
          path="/info"
          element={
            <RequireAuth>
              <Shell><InfoPage /></Shell>
            </RequireAuth>
          }
        />
        <Route
          path="/admin"
          element={
            <RequireAuth>
              <Shell><HrAdminPage /></Shell>
            </RequireAuth>
          }
        />

        {/* Fallbacks */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
