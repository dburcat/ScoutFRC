import React, { useEffect, useState, useRef } from 'react';
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
import { MatchVisualizationPage } from '@/pages/MatchVisualizationPage';
import AllianceBuilderPage from '@/pages/AllianceBuilderPage';
import ObservationFormPage from '@/pages/ObservationFormPage';
import ObservationsPage from '@/pages/ObservationsPage';
import EventAnalyticsPage from '@/pages/EventAnalyticsPage';
import MobileScoutPage from '@/pages/MobileScoutPage';

// Routes that require a logged-in user
const PROTECTED_PATHS = ['/alliance', '/observations/new'];

function AppShell() {
  const queryClient = useQueryClient();
  const [syncToast, setSyncToast] = useState<string | null>(null);

  const syncStatus = useSyncStatus();

  // Only invalidate queries when last_sync timestamp actually changes —
  // prevents flooding the app with refetches on every 3s poll tick
  const lastSyncRef = useRef<string | null>(null);
  useEffect(() => {
    const newSync = syncStatus.data?.last_sync ?? null;
    if (newSync && newSync !== lastSyncRef.current) {
      lastSyncRef.current = newSync;
      queryClient.invalidateQueries({ queryKey: ['events'] });
      queryClient.invalidateQueries({ queryKey: ['teams'] });
      queryClient.invalidateQueries({ queryKey: ['matches'] });
    }
  }, [syncStatus.data?.last_sync, queryClient]);

  // Listen for offline queue sync completions and show a toast
  useEffect(() => {
    const handler = (e: Event) => {
      const count = (e as CustomEvent<{ count: number }>).detail.count;
      setSyncToast(`${count} offline observation${count !== 1 ? 's' : ''} synced`);
      setTimeout(() => setSyncToast(null), 4000);
    };
    window.addEventListener('offline-sync-complete', handler);
    return () => window.removeEventListener('offline-sync-complete', handler);
  }, []);

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
          <Route path="/matches/:matchId/visualization" element={<MatchVisualizationPage />} />
          <Route path="/events/:eventId/analytics" element={<EventAnalyticsPage />} />
          <Route path="/alliance"  element={<AuthGate><AllianceBuilderPage /></AuthGate>} />
          <Route path="/observations" element={<ObservationsPage />} />
          <Route path="/observations/new" element={<AuthGate><ObservationFormPage /></AuthGate>} />
          {/* Tier 10 — Mobile PWA scouting form (no auth required — works offline) */}
          <Route path="/scout" element={<MobileScoutPage />} />
          {/* Placeholder routes — built in later tiers */}
          <Route path="/analytics" element={<PlaceholderPage title="Analytics" />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>

      {/* Offline sync toast */}
      {syncToast && (
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 flex items-center gap-2 px-4 py-2.5 bg-green-900/90 border border-green-700/60 rounded-xl text-green-300 text-sm font-medium shadow-lg backdrop-blur-sm animate-fade-in">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
          {syncToast}
        </div>
      )}
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