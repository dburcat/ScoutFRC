import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  CalendarDays,
  Users,
  BarChart2,
  Star,
  ClipboardPen,
  RefreshCw,
  LogOut,
  ChevronRight,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import api from '@/api/client';
import { clsx } from 'clsx';

type SyncState = 'idle' | 'syncing' | 'done' | 'error';

const NAV_ITEMS = [
  { to: '/',          icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/events',    icon: CalendarDays,    label: 'Events' },
  { to: '/teams',     icon: Users,           label: 'Teams' },
  { to: '/analytics', icon: BarChart2,       label: 'Analytics' },
  { to: '/alliance',  icon: Star,            label: 'Alliance Builder' },
];

const SCOUT_ITEMS = [
  { to: '/observations/new', icon: ClipboardPen, label: 'Add Observation' },
];

function roleLabel(role: string) {
  return role.replace(/_/g, ' ');
}

function initials(username: string) {
  const parts = username.split(/[\s_-]/);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return username.slice(0, 2).toUpperCase();
}

export default function Sidebar() {
  const { user, logout } = useAuth();
  const [syncState, setSyncState] = useState<SyncState>('idle');
  const [lastSynced, setLastSynced] = useState<Date | null>(null);
  const [syncEventKey, setSyncEventKey] = useState('');
  const [showSyncInput, setShowSyncInput] = useState(false);

  const syncLabel = () => {
    if (syncState === 'syncing') return 'Syncing with TBA…';
    if (syncState === 'error')   return 'Sync failed';
    if (syncState === 'done' && lastSynced) {
      const diff = Math.round((Date.now() - lastSynced.getTime()) / 1000);
      if (diff < 10) return 'Synced just now';
      if (diff < 60) return `Synced ${diff}s ago`;
      return `Synced ${Math.round(diff / 60)}m ago`;
    }
    return 'Ready to sync';
  };

  const handleSync = async () => {
    if (syncState === 'syncing') return;
    if (!syncEventKey.trim()) {
      setShowSyncInput(true);
      return;
    }
    setSyncState('syncing');
    setShowSyncInput(false);
    try {
      await api.post(`/admin/sync-event/${syncEventKey.trim()}`);
      setSyncState('done');
      setLastSynced(new Date());
      setSyncEventKey('');
      setTimeout(() => setSyncState('idle'), 8000);
    } catch {
      setSyncState('error');
      setTimeout(() => setSyncState('idle'), 4000);
    }
  };

  const pulseColor = clsx('w-1.5 h-1.5 rounded-full flex-shrink-0', {
    'bg-slate-600':           syncState === 'idle',
    'bg-brand animate-pulse': syncState === 'syncing',
    'bg-green-500':           syncState === 'done',
    'bg-red-500':             syncState === 'error',
  });

  const labelColor = clsx('text-xs', {
    'text-slate-600': syncState === 'idle',
    'text-brand':     syncState === 'syncing',
    'text-green-400': syncState === 'done',
    'text-red-400':   syncState === 'error',
  });

  return (
    <aside className="flex flex-col w-52 min-w-[208px] bg-app-sidebar border-r border-app-border">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-4 py-[15px] border-b border-app-border">
        <div className="w-7 h-7 rounded-md bg-brand flex items-center justify-center flex-shrink-0">
          <svg width="15" height="15" fill="none" viewBox="0 0 24 24">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"
              stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
        <span className="text-sm font-medium text-white tracking-tight">ScouterFRC</span>
      </div>

      {/* Nav */}
      <div className="flex-1 overflow-y-auto py-2">
        <p className="px-4 pt-2 pb-1 text-[10px] uppercase tracking-widest text-slate-600">
          Navigation
        </p>
        {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-2.5 mx-1.5 px-3 py-[7px] rounded-lg text-[13px] transition-colors',
                isActive
                  ? 'bg-brand/10 text-brand'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-app-card'
              )
            }
          >
            <Icon size={15} className="flex-shrink-0" />
            {label}
          </NavLink>
        ))}

        <p className="px-4 pt-4 pb-1 text-[10px] uppercase tracking-widest text-slate-600">
          Scouting
        </p>
        {SCOUT_ITEMS.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-2.5 mx-1.5 px-3 py-[7px] rounded-lg text-[13px] transition-colors',
                isActive
                  ? 'bg-brand/10 text-brand'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-app-card'
              )
            }
          >
            <Icon size={15} className="flex-shrink-0" />
            {label}
          </NavLink>
        ))}

        {/* TBA Sync */}
        <p className="px-4 pt-4 pb-1 text-[10px] uppercase tracking-widest text-slate-600">
          Data
        </p>
        <div className="mx-1.5 rounded-lg border border-app-border overflow-hidden">
          <button
            onClick={handleSync}
            disabled={syncState === 'syncing'}
            className="flex items-center gap-2.5 w-full px-3 py-[7px] text-[13px] text-slate-400 hover:text-slate-200 hover:bg-app-card transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <RefreshCw
              size={15}
              className={clsx('flex-shrink-0 transition-transform', syncState === 'syncing' && 'animate-spin')}
            />
            TBA Sync
          </button>

          {showSyncInput && (
            <div className="px-3 py-2 border-t border-app-border bg-app-card flex gap-1.5 items-center">
              <input
                autoFocus
                type="text"
                value={syncEventKey}
                onChange={e => setSyncEventKey(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') handleSync(); if (e.key === 'Escape') setShowSyncInput(false); }}
                placeholder="e.g. 2025calv"
                className="flex-1 bg-app-muted text-white text-xs px-2 py-1 rounded border border-app-border outline-none focus:border-brand/60 placeholder:text-slate-600 font-mono min-w-0"
              />
              <button
                onClick={handleSync}
                className="text-brand hover:text-brand-400 transition-colors flex-shrink-0"
              >
                <ChevronRight size={14} />
              </button>
            </div>
          )}

          <div className="flex items-center gap-2 px-3 py-[7px] border-t border-app-border">
            <div className={pulseColor} />
            <span className={labelColor}>{syncLabel()}</span>
          </div>
        </div>
      </div>

      {/* User */}
      <div className="border-t border-app-border p-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-7 h-7 rounded-full bg-brand/20 flex items-center justify-center flex-shrink-0 text-[11px] font-medium text-brand">
              {user ? initials(user.username) : '??'}
            </div>
            <div className="min-w-0">
              <p className="text-xs font-medium text-white truncate leading-tight">
                {user?.username ?? 'Unknown'}
              </p>
              <p className="text-[10px] text-slate-600 truncate capitalize">
                {user ? roleLabel(user.role) : ''}
              </p>
            </div>
          </div>
          <button
            onClick={logout}
            title="Log out"
            className="text-slate-600 hover:text-slate-400 transition-colors flex-shrink-0"
          >
            <LogOut size={14} />
          </button>
        </div>
      </div>
    </aside>
  );
}