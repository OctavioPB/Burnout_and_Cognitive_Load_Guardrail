import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Sprint 7 will wire these up — scaffolded for routing structure */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<PlaceholderPage title="Dashboard Home" />} />
        <Route path="/team/:teamId" element={<PlaceholderPage title="Team Drill-Down" />} />
        <Route path="/alerts" element={<PlaceholderPage title="Alert Feed" />} />
        <Route path="*" element={<PlaceholderPage title="404 — Not Found" />} />
      </Routes>
    </BrowserRouter>
  );
}

function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="min-h-screen bg-light flex items-center justify-center">
      <div className="text-center">
        <p className="font-body text-mid text-sm uppercase tracking-widest mb-3">
          Sprint 1 — Infrastructure Skeleton
        </p>
        <h1
          className="font-display text-primary"
          style={{ fontSize: 32, fontWeight: 300 }}
        >
          {title}
        </h1>
        <p className="font-body text-mid mt-4 text-sm">
          UI implementation begins in Sprint 7.
        </p>
      </div>
    </div>
  );
}
