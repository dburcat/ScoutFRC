import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  CalendarDays,
  Users,
  BarChart2,
  Star,
  ClipboardPen,
  RefreshCw,
  Download,
  LogOut,
  LogIn,
  ChevronRight,
  Lock,
  Database,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useSyncStatus } from '@/hooks/useSyncStatus';
import api from '@/api/client';
import { clsx } from 'clsx';

type SyncState = 'idle' | 'syncing' | 'done' | 'error';

const AUTH_REQUIRED = new Set(['/alliance', '/observations/new']);

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

function SyncStatusDot({ state }: { state: SyncState }) {
  return (
    <div className={clsx('w-1.5 h-1.5 rounded-full flex-shrink-0', {
      'bg-slate-600':           state === 'idle',
      'bg-brand animate-pulse': state === 'syncing',
      'bg-green-500':           state === 'done',
      'bg-red-500':             state === 'error',
    })} />
  );
}

export default function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  // Season bootstrap state
  const [seasonState, setSeasonState]       = useState<SyncState>('idle');
  const [seasonYear, setSeasonYear]         = useState(String(new Date().getFullYear()));
  const [showSeasonInput, setShowSeasonInput] = useState(false);
  const [seasonMsg, setSeasonMsg]           = useState('');

  // Single event sync state
  const [eventState, setEventState]         = useState<SyncState>('idle');
  const [eventKey, setEventKey]             = useState('');
  const [showEventInput, setShowEventInput] = useState(false);
  const [eventMsg, setEventMsg]             = useState('');

  const handleSeasonBootstrap = async () => {
    if (seasonState === 'syncing') return;
    if (!showSeasonInput) { setShowSeasonInput(true); return; }
    const year = parseInt(seasonYear);
    if (!year || year < 1992 || year > 2100) {
      setSeasonMsg('Enter a valid year');
      return;
    }
    setSeasonState('syncing');
    setSeasonMsg(`Fetching all ${year} events…`);
    try {
      const res = await api.post<{ events_synced: number }>(`/admin/sync-season/${year}`);
      setSeasonState('done');
      setSeasonMsg(`✓ ${res.data.events_synced} events imported`);
      setShowSeasonInput(false);
      setTimeout(() => { setSeasonState('idle'); setSeasonMsg(''); }, 10000);
    } catch {
      setSeasonState('error');
      setSeasonMsg(err?.response?.data?.detail ?? 'Bootstrap failed');
      setTimeout(() => { setSeasonState('idle'); setSeasonMsg(''); }, 6000);
    }
  };

  const handleEventSync = async () => {
    if (eventState === 'syncing') return;
    if (!showEventInput) { setShowEventInput(true); return; }
    const key = eventKey.trim();
    if (!key) { setEventMsg('Enter an event key'); return; }
    setEventState('syncing');
    setEventMsg(`Syncing ${key}…`);
    try {
      const res = await api.post<{ teams_synced: number; matches_synced: number }>(
        `/admin/sync-event/${key}`
      );
      setEventState('done');
      setEventMsg(`✓ ${res.data.teams_synced} teams, ${res.data.matches_synced} matches`);
      setEventKey('');
      setShowEventInput(false);
      setTimeout(() => { setEventState('idle'); setEventMsg(''); }, 10000);
    } catch (err: any) {
      setEventState('error');
      const detail = err?.response?.data?.detail ?? 'Sync failed';
      setEventMsg(detail.includes('404') ? 'Event key not found on TBA' : detail);
      setTimeout(() => { setEventState('idle'); setEventMsg(''); }, 6000);
    }
  };

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

        {/* ── Data section ── */}
        <p className="px-4 pt-4 pb-1 text-[10px] uppercase tracking-widest text-slate-600">
          Data
        </p>

        {/* 1. Season Bootstrap */}
        <div className="mx-1.5 mb-1.5 rounded-lg border border-app-border overflow-hidden">
          <button
            onClick={handleSeasonBootstrap}
            disabled={seasonState === 'syncing'}
            className="flex items-center gap-2.5 w-full px-3 py-[7px] text-[13px] text-slate-400 hover:text-slate-200 hover:bg-app-card transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Download
              size={15}
              className={clsx('flex-shrink-0', seasonState === 'syncing' && 'animate-pulse')}
            />
            <span className="flex-1 text-left">Bootstrap Season</span>
          </button>

          {showSeasonInput && (
            <div className="px-3 py-2 border-t border-app-border bg-app-card flex gap-1.5 items-center">
              <input
                autoFocus
                type="number"
                value={seasonYear}
                onChange={e => setSeasonYear(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter') handleSeasonBootstrap();
                  if (e.key === 'Escape') setShowSeasonInput(false);
                }}
                placeholder="e.g. 2026"
                className="flex-1 bg-app-muted text-white text-xs px-2 py-1 rounded border border-app-border outline-none focus:border-brand/60 placeholder:text-slate-600 font-mono min-w-0"
              />
              <button onClick={handleSeasonBootstrap} className="text-brand flex-shrink-0">
                <ChevronRight size={14} />
              </button>
            </div>
          )}

          {(seasonMsg || seasonState !== 'idle') && (
            <div className="flex items-start gap-2 px-3 py-[7px] border-t border-app-border">
              <SyncStatusDot state={seasonState} />
              <span className={clsx('text-[11px] leading-tight', {
                'text-slate-600': seasonState === 'idle',
                'text-brand':     seasonState === 'syncing',
                'text-green-400': seasonState === 'done',
                'text-red-400':   seasonState === 'error',
              })}>
                {seasonMsg || (seasonState === 'idle' ? 'Import all season events' : '')}
              </span>
            </div>
          )}

          {!seasonMsg && seasonState === 'idle' && (
            <div className="flex items-center gap-2 px-3 py-[7px] border-t border-app-border">
              <SyncStatusDot state="idle" />
              <span className="text-[11px] text-slate-600">Import all season events</span>
            </div>
          )}
        </div>

        {/* 2. Single Event Sync */}
        <div className="mx-1.5 rounded-lg border border-app-border overflow-hidden">
          <button
            onClick={handleEventSync}
            disabled={eventState === 'syncing'}
            className="flex items-center gap-2.5 w-full px-3 py-[7px] text-[13px] text-slate-400 hover:text-slate-200 hover:bg-app-card transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <RefreshCw
              size={15}
              className={clsx('flex-shrink-0', eventState === 'syncing' && 'animate-spin')}
            />
            <span className="flex-1 text-left">Sync Event</span>
          </button>

          {showEventInput && (
            <div className="px-3 py-2 border-t border-app-border bg-app-card flex gap-1.5 items-center">
              <input
                autoFocus
                type="text"
                value={eventKey}
                onChange={e => setEventKey(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter') handleEventSync();
                  if (e.key === 'Escape') setShowEventInput(false);
                }}
                placeholder="e.g. 2026calv"
                className="flex-1 bg-app-muted text-white text-xs px-2 py-1 rounded border border-app-border outline-none focus:border-brand/60 placeholder:text-slate-600 font-mono min-w-0"
              />
              <button onClick={handleEventSync} className="text-brand flex-shrink-0">
                <ChevronRight size={14} />
              </button>
            </div>
          )}

          {(eventMsg || eventState !== 'idle') && (
            <div className="flex items-start gap-2 px-3 py-[7px] border-t border-app-border">
              <SyncStatusDot state={eventState} />
              <span className={clsx('text-[11px] leading-tight', {
                'text-slate-600': eventState === 'idle',
                'text-brand':     eventState === 'syncing',
                'text-green-400': eventState === 'done',
                'text-red-400':   eventState === 'error',
              })}>
                {eventMsg || ''}
              </span>
            </div>
          )}

          {!eventMsg && eventState === 'idle' && (
            <div className="flex items-center gap-2 px-3 py-[7px] border-t border-app-border">
              <SyncStatusDot state="idle" />
              <span className="text-[11px] text-slate-600">Teams + matches per event</span>
            </div>
          )}
        </div>
      </div>

      {/* User / Sign-in */}
      <div className="border-t border-app-border p-3">
        {user ? (
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
        ) : (
          <button
            onClick={() => navigate('/login')}
            className="flex items-center gap-2 w-full px-3 py-2 rounded-lg bg-app-card border border-app-border hover:border-brand/40 hover:bg-brand/5 transition-all text-[13px] text-slate-400 hover:text-brand"
          >
            <LogIn size={14} className="flex-shrink-0" />
            <span>Sign in</span>
            <span className="ml-auto text-[10px] text-slate-600">to scout</span>
          </button>
        )}
      </div>
    </aside>
  );
}