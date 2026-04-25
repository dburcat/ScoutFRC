import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import Sidebar from '@/pages/Sidebar';
import LoginPage from '@/pages/LoginPage';
import DashboardPage from '@/pages/DashboardPage';
import EventsPage from '@/pages/EventsPage';

function AppShell() {
  return (
    <div className="flex min-h-screen w-full bg-app-bg">
      <Sidebar />
      <main className="flex-1 min-w-0 flex flex-col">
        <Routes>
          <Route path="/"        element={<DashboardPage />} />
          <Route path="/events"  element={<EventsPage />} />
          {/* Placeholder routes — to be built in later tiers */}
          <Route path="/teams"     element={<PlaceholderPage title="Teams" />} />
          <Route path="/analytics" element={<PlaceholderPage title="Analytics" />} />
          <Route path="/alliance"  element={<PlaceholderPage title="Alliance Builder" />} />
          <Route path="/observations/new" element={<PlaceholderPage title="Add Observation" />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
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

function ProtectedRoutes() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-app-bg">
        <div className="flex items-center gap-2 text-slate-600 text-sm">
          <div className="w-1.5 h-1.5 rounded-full bg-brand animate-pulse" />
          Loading…
        </div>
      </div>
    );
  }

  if (!user) return <Navigate to="/login" replace />;
  return <AppShell />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/*"     element={<ProtectedRoutes />} />
    </Routes>
  );
}