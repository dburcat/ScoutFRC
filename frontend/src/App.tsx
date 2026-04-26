import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import Sidebar from '@/pages/Sidebar';
import LoginPage from '@/pages/LoginPage';
import DashboardPage from '@/pages/DashboardPage';
import EventsPage from '@/pages/EventsPage';

// Routes that require a logged-in user
const PROTECTED_PATHS = ['/alliance', '/observations/new'];

function AppShell() {
  return (
    <div className="flex min-h-screen w-full bg-app-bg">
      <Sidebar />
      <main className="flex-1 min-w-0 flex flex-col">
        <Routes>
          <Route path="/"        element={<DashboardPage />} />
          <Route path="/events"  element={<EventsPage />} />
          {/* Placeholder routes — built in later tiers */}
          <Route path="/teams"     element={<PlaceholderPage title="Teams" />} />
          <Route path="/analytics" element={<PlaceholderPage title="Analytics" />} />
          <Route path="/alliance"  element={<AuthGate><PlaceholderPage title="Alliance Builder" /></AuthGate>} />
          <Route path="/observations/new" element={<AuthGate><PlaceholderPage title="Add Observation" /></AuthGate>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

/** Wraps a route that needs auth — redirects to /login if not signed in */
function AuthGate({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) return <LoadingSpinner />;
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />;
  return <>{children}</>;
}

function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="text-center">
        <p className="text-slate-600 text-sm font-mono">{title}</p>
        <p className="text-slate-700 text-xs mt-1">Coming in a future tier</p>
      </div>
    </div>
  );
}

function LoadingSpinner() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-app-bg">
      <div className="flex items-center gap-2 text-slate-600 text-sm">
        <div className="w-1.5 h-1.5 rounded-full bg-brand animate-pulse" />
        Loading…
      </div>
    </div>
  );
}

export default function App() {
  const { isLoading } = useAuth();

  // Wait for auth check before rendering anything to avoid flash
  if (isLoading) return <LoadingSpinner />;

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      {/* All other routes get the shell — individual routes guard themselves */}
      <Route path="/*" element={<AppShell />} />
    </Routes>
  );
}