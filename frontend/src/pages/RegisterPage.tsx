import { useState, FormEvent } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import api from '@/api/client';
import { AuthResponse } from '@/types/auth';

export default function RegisterPage() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [username, setUsername]               = useState('');
  const [email, setEmail]                     = useState('');
  const [password, setPassword]               = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError]                     = useState('');
  const [isLoading, setIsLoading]             = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setIsLoading(true);
    try {
      // 1. Create the account
      await api.post('/users/', { username, email, password, role: 'SCOUT' });

      // 2. Immediately log in so the user lands authenticated
      const params = new URLSearchParams();
      params.append('username', username);
      params.append('password', password);
      const res = await api.post<AuthResponse>('/login', params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });
      await login(res.data);
      navigate('/', { replace: true });
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      if (typeof detail === 'string') {
        setError(detail);
      } else {
        setError('Registration failed. Please try again.');
      }
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
          <h1 className="text-white font-medium text-base mb-1">Create account</h1>
          <p className="text-slate-500 text-xs mb-5">Join your team on ScouterFRC</p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1.5">Username</label>
              <input
                type="text"
                value={username}
                onChange={e => setUsername(e.target.value)}
                required
                autoFocus
                autoComplete="username"
                className="w-full bg-app-muted border border-app-border rounded-lg px-3 py-2 text-sm text-white placeholder:text-slate-600 outline-none focus:border-brand/60 transition-colors font-mono"
                placeholder="your_username"
              />
            </div>

            <div>
              <label className="block text-xs text-slate-400 mb-1.5">Email</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                autoComplete="email"
                className="w-full bg-app-muted border border-app-border rounded-lg px-3 py-2 text-sm text-white placeholder:text-slate-600 outline-none focus:border-brand/60 transition-colors"
                placeholder="you@example.com"
              />
            </div>

            <div>
              <label className="block text-xs text-slate-400 mb-1.5">Password</label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                autoComplete="new-password"
                className="w-full bg-app-muted border border-app-border rounded-lg px-3 py-2 text-sm text-white placeholder:text-slate-600 outline-none focus:border-brand/60 transition-colors"
                placeholder="min. 8 characters"
              />
            </div>

            <div>
              <label className="block text-xs text-slate-400 mb-1.5">Confirm password</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={e => setConfirmPassword(e.target.value)}
                required
                autoComplete="new-password"
                className={`w-full bg-app-muted border rounded-lg px-3 py-2 text-sm text-white placeholder:text-slate-600 outline-none transition-colors ${
                  confirmPassword && confirmPassword !== password
                    ? 'border-red-500/60 focus:border-red-500/80'
                    : 'border-app-border focus:border-brand/60'
                }`}
                placeholder="••••••••"
              />
              {confirmPassword && confirmPassword !== password && (
                <p className="text-red-400 text-[11px] mt-1">Passwords don't match</p>
              )}
            </div>

            {error && (
              <p className="text-red-400 text-xs bg-red-900/20 border border-red-900/40 rounded-lg px-3 py-2">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={isLoading || (!!confirmPassword && confirmPassword !== password)}
              className="w-full bg-brand hover:bg-brand-600 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg py-2 transition-colors"
            >
              {isLoading ? 'Creating account…' : 'Create account'}
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-slate-600 mt-4">
          Already have an account?{' '}
          <Link to="/login" className="text-brand hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}