import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import Sidebar from '@/components/Sidebar';
import DashboardPage from '@/pages/DashboardPage';
import LoginPage from '@/pages/LoginPage';
import EventsPage from '@/pages/EventsPage';

function App() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-sand-50 flex items-center justify-center">
        <span className="font-serif italic text-[18px] text-sand-400">Loading…</span>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-sand-50">
      {user && <Sidebar />}

      <div className={`flex flex-col flex-1 min-h-screen ${user ? 'ml-[200px]' : ''}`}>

        {/* Header — only when logged in */}
        {user && (
          <header className="h-[52px] bg-sand-50 border-b border-sand-200 flex items-center justify-end px-12 sticky top-0 z-30">
            <div className="flex items-center gap-2.5">
              <span className="font-sans text-[12px] text-sand-400">{user.username}</span>
              <div className="w-[26px] h-[26px] rounded-full bg-sand-200 border border-sand-300 flex items-center justify-center font-sans text-[11px] font-medium text-sand-600">
                {user.username.charAt(0).toUpperCase()}
              </div>
            </div>
          </header>
        )}

        {/* Routes */}
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<Navigate to="/events" replace />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/events" element={<EventsPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/teams" element={
              <div className="px-12 pt-20 text-center">
                <div className="font-serif italic text-[24px] text-sand-300">Team analytics coming soon</div>
              </div>
            } />
            <Route path="*" element={
              <div className="px-12 pt-20 text-center">
                <div className="font-serif text-[72px] text-sand-200 leading-none">404</div>
                <div className="font-sans text-[14px] text-sand-400 mt-3">This page doesn't exist.</div>
              </div>
            } />
          </Routes>
        </main>

        {/* Footer */}
        <footer className="px-12 py-6 border-t border-sand-200 flex items-center justify-between">
          <span className="font-serif italic text-[13px] text-sand-400">Scouter FRC</span>
          <span className="font-sans text-[11px] text-sand-300">
            © {new Date().getFullYear()} Unified Scouting Platform
          </span>
        </footer>
      </div>
    </div>
  );
}

export default App;