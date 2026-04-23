import { Routes, Route, Link } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import DashboardPage from '@/pages/DashboardPage';
import LoginPage from '@/pages/LoginPage';

function App() {
  const auth = useAuth();
  const user = auth?.user;
  const logout = auth?.logout;

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Navigation Bar */}
      <nav className="bg-white border-b border-gray-200 py-4 px-6 shadow-sm">
        <div className="max-w-6xl mx-auto flex justify-between items-center">
          <div className="flex items-center gap-8">
            <Link to="/" className="text-2xl font-black text-blue-600 tracking-tight">SCOUTER</Link>
            <div className="hidden md:flex gap-6 font-medium text-gray-500">
              <Link to="/" className="hover:text-blue-600 transition-colors">Dashboard</Link>
              <span className="cursor-not-allowed opacity-50">Events</span>
              <span className="cursor-not-allowed opacity-50">Teams</span>
            </div>
          </div>
          
          <div>
            {user ? (
              <div className="flex gap-4 items-center">
                <span className="text-sm">Hi, <b>{user.username}</b></span>
                <button onClick={logout} className="text-xs bg-gray-200 px-3 py-1 rounded-md hover:bg-gray-300">Logout</button>
              </div>
            ) : (
              <Link to="/login" className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-blue-700 transition-all">Login</Link>
            )}
          </div>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="flex-grow max-w-6xl w-full mx-auto p-6">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/login" element={<LoginPage />} />
        </Routes>
      </main>
      
      {/* Task 5.9 Shared Footer */}
      <footer className="p-8 text-center text-gray-400 text-sm border-t border-gray-200">
        &copy; 2026 ScouterFRC • Phase 1 Build
      </footer>
    </div>
  );
}

export default App;