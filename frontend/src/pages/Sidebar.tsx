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
  Menu,
  X,
  type LucideIcon,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useSyncStatus } from '@/hooks/useSyncStatus';
import { clsx } from 'clsx';

type SyncState = 'idle' | 'syncing' | 'done' | 'error';

const AUTH_REQUIRED = new Set(['/alliance', '/observations/new']);

const NAV_ITEMS: { to: string; icon: LucideIcon; label: string }[] = [
  { to: '/dashboard',   icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/events',      icon: CalendarDays,    label: 'Events' },
  { to: '/teams',       icon: Users,           label: 'Teams' },
  { to: '/alliance',    icon: BarChart2,       label: 'Alliance' },
];

const SCOUT_ITEMS: { to: string; icon: LucideIcon; label: string }[] = [
  { to: '/observations',     icon: ClipboardPen, label: 'Observations' },
  { to: '/observations/new', icon: Star,         label: 'New Observation' },
];

function initials(name: string) {
  return name.slice(0, 2).toUpperCase();
}

function roleLabel(role: string) {
  return role.replace('_', ' ').toLowerCase();
}

function SidebarContent({ onNav }: { onNav?: () => void }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const syncStatus = useSyncStatus();
  const isAutoSyncing = syncStatus.data?.scheduler_running;
  const hasData = (syncStatus.data?.events_count ?? 0) > 0;
  const lastSync = syncStatus.data?.last_sync ? new Date(syncStatus.data.last_sync) : null;
  const lastSyncTime = lastSync
    ? lastSync.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
    : 'Never';

  return (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-3 py-2 border-b border-app-border">
        <svg width="160" height="100" viewBox="180 110 320 270" xmlns="http://www.w3.org/2000/svg" aria-label="ScouterFRC logo" role="img" className="flex-shrink-0">
          <polygon points="340,140 400,174 400,242 340,276 280,242 280,174" fill="none" stroke="#2563eb" strokeWidth="2.5"/>
          <line x1="400" y1="174" x2="440" y2="155" stroke="#1e3a5f" strokeWidth="1.5"/>
          <line x1="440" y1="155" x2="462" y2="155" stroke="#1e3a5f" strokeWidth="1.5"/>
          <circle cx="462" cy="155" r="3" fill="#1e3a5f"/>
          <line x1="400" y1="242" x2="440" y2="261" stroke="#1e3a5f" strokeWidth="1.5"/>
          <line x1="440" y1="261" x2="462" y2="261" stroke="#1e3a5f" strokeWidth="1.5"/>
          <circle cx="462" cy="261" r="3" fill="#1e3a5f"/>
          <line x1="280" y1="174" x2="240" y2="155" stroke="#1e3a5f" strokeWidth="1.5"/>
          <line x1="240" y1="155" x2="218" y2="155" stroke="#1e3a5f" strokeWidth="1.5"/>
          <circle cx="218" cy="155" r="3" fill="#1e3a5f"/>
          <line x1="280" y1="242" x2="240" y2="261" stroke="#1e3a5f" strokeWidth="1.5"/>
          <line x1="240" y1="261" x2="218" y2="261" stroke="#1e3a5f" strokeWidth="1.5"/>
          <circle cx="218" cy="261" r="3" fill="#1e3a5f"/>
          <line x1="340" y1="140" x2="340" y2="118" stroke="#1e3a5f" strokeWidth="1.5"/>
          <circle cx="340" cy="118" r="3" fill="#1e3a5f"/>
          <line x1="340" y1="276" x2="340" y2="298" stroke="#1e3a5f" strokeWidth="1.5"/>
          <circle cx="340" cy="298" r="3" fill="#1e3a5f"/>
          <line x1="295" y1="248" x2="385" y2="248" stroke="#1e3a5f" strokeWidth="1.5" strokeLinecap="round"/>
          <rect x="298" y="234" width="12" height="14" rx="2" fill="#1e3a5f"/>
          <rect x="314" y="224" width="12" height="24" rx="2" fill="#1e3a5f"/>
          <rect x="330" y="216" width="12" height="32" rx="2" fill="#2563eb"/>
          <rect x="346" y="204" width="12" height="44" rx="2" fill="#2563eb"/>
          <rect x="362" y="192" width="12" height="56" rx="2" fill="#60a5fa"/>
          <polyline points="304,231 320,221 336,213 352,201 368,189" stroke="#f59e0b" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
          <circle cx="368" cy="189" r="4" fill="#f59e0b"/>
          <text x="340" y="338" textAnchor="middle" fontFamily="system-ui, sans-serif" fontSize="42" fontWeight="500" letterSpacing="-1">
            <tspan fill="#3b82f6">Scouter</tspan><tspan fill="#f1f5f9">FRC</tspan>
          </text>
          <text x="340" y="360" textAnchor="middle" fontFamily="system-ui, sans-serif" fontSize="14" fontWeight="400" letterSpacing="3" fill="#64748b">COMPETITION INTELLIGENCE</text>
        </svg>
      </div>

      {/* Sign-in Button */}
      {!user && (
        <div className="px-3 py-2.5 border-b border-app-border">
          <button
            onClick={() => { navigate('/login'); onNav?.(); }}
            className="flex items-center gap-2 w-full px-3 py-2 rounded-lg bg-app-card border border-app-border hover:border-brand/40 hover:bg-brand/5 transition-all text-[13px] text-slate-400 hover:text-brand"
          >
            <LogIn size={14} className="flex-shrink-0" />
            <span>Sign in</span>
            <span className="ml-auto text-[10px] text-slate-600">to scout</span>
          </button>
        </div>
      )}

      {/* User Profile */}
      {user && (
        <div className="border-b border-app-border p-3">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <div className="w-7 h-7 rounded-full bg-brand/20 flex items-center justify-center flex-shrink-0 text-[11px] font-medium text-brand">
                {initials(user.username)}
              </div>
              <div className="min-w-0">
                <p className="text-xs font-medium text-white truncate leading-tight">{user.username}</p>
                <p className="text-[10px] text-slate-600 truncate capitalize">{roleLabel(user.role)}</p>
              </div>
            </div>
            <button onClick={logout} title="Log out" className="text-slate-600 hover:text-slate-400 transition-colors flex-shrink-0">
              <LogOut size={14} />
            </button>
          </div>
        </div>
      )}

      {/* Nav */}
      <div className="flex-1 overflow-y-auto py-2">
        <p className="px-4 pt-2 pb-1 text-[10px] uppercase tracking-widest text-slate-600">Navigation</p>
        {NAV_ITEMS.map(({ to, icon: Icon, label }) => {
          const locked = AUTH_REQUIRED.has(to) && !user;
          return (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              onClick={onNav}
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

        <p className="px-4 pt-4 pb-1 text-[10px] uppercase tracking-widest text-slate-600">Scouting</p>
        {SCOUT_ITEMS.map(({ to, icon: Icon, label }) => {
          const locked = !user;
          return (
            <NavLink
              key={to}
              to={to}
              onClick={onNav}
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

        {/* Sync Status */}
        <p className="px-4 pt-4 pb-1 text-[10px] uppercase tracking-widest text-slate-600">Sync Status</p>
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
    </div>
  );
}

export default function Sidebar() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <>
      {/* ── Desktop sidebar — always visible, unchanged ── */}
      <aside className="hidden md:flex flex-col w-52 min-w-[208px] bg-app-sidebar border-r border-app-border">
        <SidebarContent />
      </aside>

      {/* ── Mobile hamburger button — shown in top-left on small screens ── */}
      <button
        onClick={() => setMobileOpen(true)}
        className="md:hidden fixed top-3 left-3 z-40 p-2 rounded-lg bg-app-card border border-app-border text-slate-400 hover:text-white transition-colors"
        aria-label="Open menu"
      >
        <Menu size={18} />
      </button>

      {/* ── Mobile overlay + slide-in drawer ── */}
      {mobileOpen && (
        <>
          {/* Backdrop */}
          <div
            className="md:hidden fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
          />
          {/* Drawer */}
          <aside className="md:hidden fixed top-0 left-0 z-50 h-full w-64 bg-app-sidebar border-r border-app-border flex flex-col shadow-2xl">
            <div className="flex items-center justify-end px-3 py-2 border-b border-app-border">
              <button
                onClick={() => setMobileOpen(false)}
                className="p-1.5 rounded-lg text-slate-500 hover:text-white transition-colors"
                aria-label="Close menu"
              >
                <X size={16} />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto">
              <SidebarContent onNav={() => setMobileOpen(false)} />
            </div>
          </aside>
        </>
      )}
    </>
  );
}