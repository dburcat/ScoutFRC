import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/context/AuthContext';
import { useSyncStatus } from '@/hooks/useSyncStatus';
import Sidebar from '@/pages/Sidebar';
import LoginPage from '@/pages/LoginPage';
import DashboardPage from '@/pages/DashboardPage';
import EventsPage from '@/pages/EventsPage';
import TeamsPage from '@/pages/TeamsPage';
import TeamProfilePage from '@/pages/TeamProfilePage';
import MatchDetailPage from '@/pages/MatchDetailPage';
import AllianceBuilderPage from '@/pages/AllianceBuilderPage';
import ObservationFormPage from '@/pages/ObservationFormPage';
import ObservationsPage from '@/pages/ObservationsPage';
import EventAnalyticsPage from '@/pages/EventAnalyticsPage';

// Routes that require a logged-in user
const PROTECTED_PATHS = ['/alliance', '/observations/new'];

function AppShell() {
  const queryClient = useQueryClient();
  
  // Start polling sync status on app load — available to all users including guests
  // When sync completes, refetch data queries to show fresh data
  const syncStatus = useSyncStatus();
  
  // When sync completes and we have fresh data, trigger dependent queries to refetch
  if (syncStatus.data && syncStatus.data.events_count > 0 && syncStatus.data.teams_count > 0) {
    // Invalidate queries so pages refetch fresh data
    // This is safe to call frequently — React Query deduplicates
    queryClient.invalidateQueries({ queryKey: ['events'] });
    queryClient.invalidateQueries({ queryKey: ['teams'] });
    queryClient.invalidateQueries({ queryKey: ['matches'] });
  }

  return (
    <div className="flex min-h-screen w-full bg-app-bg">
      <Sidebar />
      <main className="flex-1 min-w-0 flex flex-col">
        <Routes>
          <Route path="/"        element={<DashboardPage />} />
          <Route path="/events"  element={<EventsPage />} />
          <Route path="/teams"   element={<TeamsPage />} />
          <Route path="/teams/:teamId" element={<TeamProfilePage />} />
          <Route path="/matches/:matchId" element={<MatchDetailPage />} />
          <Route path="/events/:eventId/analytics" element={<EventAnalyticsPage />} />
          <Route path="/alliance"  element={<AuthGate><AllianceBuilderPage /></AuthGate>} />
          <Route path="/observations" element={<ObservationsPage />} />
          <Route path="/observations/new" element={<AuthGate><ObservationFormPage /></AuthGate>} />
          {/* Placeholder routes — built in later tiers */}
          <Route path="/analytics" element={<PlaceholderPage title="Analytics" />} />
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