import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  CalendarDays,
  Users,
  BarChart2,
  Star,
  ClipboardPen,
  LogOut,
  LogIn,
  Lock,
  Database,
  type LucideIcon,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useSyncStatus } from '@/hooks/useSyncStatus';
import { clsx } from 'clsx';

type SyncState = 'idle' | 'syncing' | 'done' | 'error';

const AUTH_REQUIRED = new Set(['/alliance', '/observations/new']);

export default function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  // Auto sync status — polls backend to show if sync is happening
  const syncStatus = useSyncStatus();
  const isAutoSyncing = syncStatus.data?.scheduler_running;
  const hasData = (syncStatus.data?.events_count ?? 0) > 0;
  const lastSync = syncStatus.data?.last_sync ? new Date(syncStatus.data.last_sync) : null;
  const lastSyncTime = lastSync ? lastSync.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }) : 'Never';

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

      {/* Sign-in Button (when not authenticated) */}
      {!user && (
        <div className="px-3 py-2.5 border-b border-app-border">
          <button
            onClick={() => navigate('/login')}
            className="flex items-center gap-2 w-full px-3 py-2 rounded-lg bg-app-card border border-app-border hover:border-brand/40 hover:bg-brand/5 transition-all text-[13px] text-slate-400 hover:text-brand"
          >
            <LogIn size={14} className="flex-shrink-0" />
            <span>Sign in</span>
            <span className="ml-auto text-[10px] text-slate-600">to scout</span>
          </button>
        </div>
      )}

      {/* Auto Sync Status Bar */}
      <div className={clsx('px-4 py-2 border-b border-app-border flex items-center gap-2 text-[11px]', {
        'bg-brand/10': isAutoSyncing,
        'bg-green-500/10': hasData && !isAutoSyncing,
      })}>
        <Database className={clsx('flex-shrink-0', {
          'text-brand animate-pulse': isAutoSyncing,
          'text-green-500': hasData && !isAutoSyncing,
          'text-slate-600': !hasData,
        })} size={12} />
        <div className="flex-1 min-w-0">
          <p className={clsx('text-[10px] truncate', {
            'text-brand font-medium': isAutoSyncing,
            'text-green-500': hasData && !isAutoSyncing,
            'text-slate-500': !hasData,
          })}>
            {isAutoSyncing ? 'Syncing data…' : hasData ? `Updated ${lastSyncTime}` : 'Waiting for data'}
          </p>
        </div>
      </div>

      {/* Nav */}
      <div className="flex-1 overflow-y-auto py-2">
        <p className="px-4 pt-2 pb-1 text-[10px] uppercase tracking-widest text-slate-600">
          Navigation
        </p>
        {NAV_ITEMS.map(({ to, icon: Icon, label }) => {
          const locked = AUTH_REQUIRED.has(to) && !user;
          return (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-2.5 mx-1.5 px-3 py-[7px] rounded-lg text-[13px] transition-colors',
                  isActive ? 'bg-brand/10 text-brand'
                    : locked ? 'text-slate-600 hover:text-slate-500 hover:bg-app-card'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-app-card'
                )
              }
            >
              <Icon size={15} className="flex-shrink-0" />
              <span className="flex-1">{label}</span>
              {locked && <Lock size={11} className="flex-shrink-0 text-slate-700" />}
            </NavLink>
          );
        })}

        <p className="px-4 pt-4 pb-1 text-[10px] uppercase tracking-widest text-slate-600">
          Scouting
        </p>
        {SCOUT_ITEMS.map(({ to, icon: Icon, label }) => {
          const locked = !user;
          return (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-2.5 mx-1.5 px-3 py-[7px] rounded-lg text-[13px] transition-colors',
                  isActive ? 'bg-brand/10 text-brand'
                    : locked ? 'text-slate-600 hover:text-slate-500 hover:bg-app-card'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-app-card'
                )
              }
            >
              <Icon size={15} className="flex-shrink-0" />
              <span className="flex-1">{label}</span>
              {locked && <Lock size={11} className="flex-shrink-0 text-slate-700" />}
            </NavLink>
          );
        })}

        {/* ── Data Sync Status ── */}
        <p className="px-4 pt-4 pb-1 text-[10px] uppercase tracking-widest text-slate-600">
          Sync Status
        </p>

        <div className="mx-1.5 mb-1.5 rounded-lg border border-app-border overflow-hidden">
          <div className={clsx('px-3 py-3 flex items-center justify-between', {
            'bg-brand/10': isAutoSyncing,
            'bg-green-500/10': hasData && !isAutoSyncing,
          })}>
            <div className="flex items-center gap-2.5 min-w-0">
              <Database className={clsx('flex-shrink-0', {
                'text-brand animate-pulse': isAutoSyncing,
                'text-green-500': hasData && !isAutoSyncing,
                'text-slate-600': !hasData,
              })} size={15} />
              <div className="min-w-0">
                <p className={clsx('text-[11px] truncate', {
                  'text-brand font-medium': isAutoSyncing,
                  'text-green-500': hasData && !isAutoSyncing,
                  'text-slate-500': !hasData,
                })}>
                  {isAutoSyncing ? 'Syncing data…' : hasData ? 'Sync complete' : 'No data yet'}
                </p>
                <p className={clsx('text-[10px] truncate', {
                  'text-slate-600': isAutoSyncing || (hasData && !isAutoSyncing),
                  'text-slate-700': !hasData && !isAutoSyncing,
                })}>
                  {hasData ? `Updated ${lastSyncTime}` : 'Initializing…'}
                </p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3 px-3 py-2 border-t border-app-border text-[10px] text-slate-600 bg-app-muted/20">
            <span>{syncStatus.data?.events_count ?? 0} events</span>
            <span>•</span>
            <span>{syncStatus.data?.teams_count ?? 0} teams</span>
          </div>
        </div>
      </div>

      {/* User Profile / Logout (only when authenticated) */}
      {user && (
        <div className="border-t border-app-border p-3">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <div className="w-7 h-7 rounded-full bg-brand/20 flex items-center justify-center flex-shrink-0 text-[11px] font-medium text-brand">
                {initials(user.username)}
              </div>
              <div className="min-w-0">
                <p className="text-xs font-medium text-white truncate leading-tight">
                  {user.username}
                </p>
                <p className="text-[10px] text-slate-600 truncate capitalize">
                  {roleLabel(user.role)}
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
      )}
    </aside>
  );
}

// ── Navigation Items ──────────────────────────────────────────────────────
interface NavItem {
  to: string;
  icon: LucideIcon;
  label: string;
}

const NAV_ITEMS: NavItem[] = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/events', icon: CalendarDays, label: 'Events' },
  { to: '/teams', icon: Users, label: 'Teams' },
  { to: '/alliance', icon: BarChart2, label: 'Alliance' },
];

const SCOUT_ITEMS: NavItem[] = [
  { to: '/observations', icon: ClipboardPen, label: 'Observations' },
  { to: '/observations/new', icon: Star, label: 'New Observation' },
];

// ── Helper Functions ──────────────────────────────────────────────────────
function initials(username: string): string {
  return username
    .split(' ')
    .map((word) => word[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

function roleLabel(role: string): string {
  const labels: Record<string, string> = {
    admin: 'Administrator',
    scout: 'Scout',
    viewer: 'Viewer',
  };
  return labels[role] || role;
}