import { useState, FormEvent } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import api from '@/api/client';
import { AuthResponse } from '@/types/auth';

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: { pathname: string } })?.from?.pathname ?? "/";
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    try {
      // FastAPI OAuth2 expects form-encoded body
      const params = new URLSearchParams();
      params.append('username', username);
      params.append('password', password);
      const res = await api.post<AuthResponse>('/login', params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });
      await login(res.data);
      navigate(from, { replace: true });
    } catch {
      setError('Invalid username or password');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-app-bg">
      <div className="w-full max-w-sm px-4">
        {/* Logo */}
        <div className="flex items-center gap-3 mb-8">
          <div className="w-9 h-9 rounded-lg bg-brand flex items-center justify-center">
            <svg width="18" height="18" fill="none" viewBox="0 0 24 24">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"
                stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div>
            <p className="text-white font-medium text-sm leading-tight">ScouterFRC</p>
            <p className="text-slate-600 text-xs">FRC Analytics Platform</p>
          </div>
        </div>

        <div className="bg-app-card border border-app-border rounded-xl p-6">
          <h1 className="text-white font-medium text-base mb-1">Sign in</h1>
          <p className="text-slate-500 text-xs mb-5">Enter your team credentials to continue</p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1.5">Username</label>
              <input
                type="text"
                value={username}
                onChange={e => setUsername(e.target.value)}
                required
                autoFocus
                className="w-full bg-app-muted border border-app-border rounded-lg px-3 py-2 text-sm text-white placeholder:text-slate-600 outline-none focus:border-brand/60 transition-colors font-mono"
                placeholder="your_username"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1.5">Password</label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                className="w-full bg-app-muted border border-app-border rounded-lg px-3 py-2 text-sm text-white placeholder:text-slate-600 outline-none focus:border-brand/60 transition-colors"
                placeholder="••••••••"
              />
            </div>

            {error && (
              <p className="text-red-400 text-xs bg-red-900/20 border border-red-900/40 rounded-lg px-3 py-2">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-brand hover:bg-brand-600 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg py-2 transition-colors"
            >
              {isLoading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}