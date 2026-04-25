import React, { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import api from '@/api/client';
import { AuthResponse } from '@/types/auth';

const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError]       = useState('');
  const [loading, setLoading]   = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const params = new URLSearchParams();
      params.append('username', username);
      params.append('password', password);
      const response = await api.post<AuthResponse>('/login', params);
      await login(response.data);
    } catch {
      setError('Invalid username or password');
    } finally {
      setLoading(false);
    }
  };

  const inputClass = `
    w-full px-3 py-2.5 rounded-md border border-sand-300 bg-white
    font-sans text-[14px] text-sand-900 outline-none
    focus:border-sand-500 transition-colors
  `;

  const labelClass = 'block font-sans text-[12px] font-medium text-sand-600 mb-1.5 tracking-wide';

  return (
    <div className="flex min-h-screen bg-sand-50">

      {/* Left panel */}
      <div className="w-[420px] min-h-screen bg-sand-100 border-r border-sand-300 flex flex-col justify-between px-10 py-12 shrink-0">
        <div>
          <div className="font-serif text-[26px] text-sand-900">Scouter</div>
          <div className="font-serif italic text-[14px] text-sand-500 mt-1">FRC Analytics</div>
        </div>

        <div>
          <h1 className="font-serif text-[42px] text-sand-900 leading-[1.15] mb-4">
            Unified<br /><em>scouting</em><br />platform.
          </h1>
          <p className="font-sans text-[14px] text-sand-500 leading-relaxed max-w-[280px]">
            Real-time match data, team analytics, and alliance selection tools for FRC competitions.
          </p>
        </div>

        <div className="font-sans text-[11px] text-sand-400">
          © {new Date().getFullYear()} Scouter FRC
        </div>
      </div>

      {/* Right panel */}
      <div className="flex-1 flex items-center justify-center p-12">
        <div className="w-full max-w-[340px]">
          <h2 className="font-serif text-[28px] text-sand-900 mb-2">Sign in</h2>
          <p className="font-sans text-[13px] text-sand-500 mb-8">Enter your credentials to continue</p>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-md px-4 py-2.5 mb-5 font-sans text-[13px] text-red-800">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <label className={labelClass}>Username</label>
              <input
                type="text"
                value={username}
                onChange={e => setUsername(e.target.value)}
                className={inputClass}
                required
              />
            </div>
            <div>
              <label className={labelClass}>Password</label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                className={inputClass}
                required
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="mt-2 w-full py-2.5 bg-sand-900 text-sand-50 rounded-md font-sans text-[14px] font-medium hover:bg-sand-600 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;