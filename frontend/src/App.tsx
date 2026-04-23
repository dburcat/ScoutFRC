import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import Sidebar from '@/components/Sidebar';
import DashboardPage from '@/pages/DashboardPage';
import LoginPage from '@/pages/LoginPage';
import EventsPage from '@/pages/EventsPage';

function App() {
  const auth = useAuth();
  const user = auth?.user;

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* 1. Fixed Sidebar on the left */}
      <Sidebar />

      {/* 2. Main Content Container */}
      {/* ml-64 (16rem) compensates for the fixed sidebar width */}
      <div className="flex-1 flex flex-col ml-64 transition-all duration-300">
        
        {/* Top Header - For User Profile/Status */}
        <header className="bg-white border-b border-gray-200 h-16 flex items-center justify-end px-8 sticky top-0 z-10">
          {user ? (
            <div className="flex gap-4 items-center">
              <span className="text-sm text-gray-600">
                Logged in as <b className="text-gray-900">{user.username}</b>
              </span>
              <div className="h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-bold text-xs">
                {user.username.charAt(0).toUpperCase()}
              </div>
            </div>
          ) : (
            <div className="text-sm text-gray-400 font-medium italic">Guest Mode</div>
          )}
        </header>

        {/* 3. Page Routing Area */}
        <main className="p-8 max-w-7xl w-full mx-auto">
          <Routes>
            {/* Redirect root to /events so the user selects a competition first */}
            <Route path="/" element={<Navigate to="/events" replace />} />
            
            <Route path="/login" element={<LoginPage />} />
            <Route path="/events" element={<EventsPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            
            {/* Future Team Profile route */}
            <Route path="/teams" element={
              <div className="py-20 text-center border-2 border-dashed border-gray-200 rounded-2xl">
                <p className="text-gray-400 font-medium text-lg">Team Analytics coming soon!</p>
              </div>
            } />

            {/* 404 Catch-all */}
            <Route path="*" element={
              <div className="py-20 text-center">
                <h1 className="text-4xl font-black text-gray-200">404</h1>
                <p className="text-gray-500">This page doesn't exist.</p>
              </div>
            } />
          </Routes>
        </main>

        {/* Shared Footer */}
        <footer className="mt-auto p-8 text-center text-gray-400 text-xs border-t border-gray-100 bg-white/50">
          &copy; {new Date().getFullYear()} Scouter FRC Analyzer • Unified Scouting Platform
        </footer>
      </div>
    </div>
  );
}

export default App;