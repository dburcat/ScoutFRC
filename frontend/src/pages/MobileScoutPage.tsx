/**
 * MobileScoutPage.tsx
 * ===================
 * Phase 2 Tier 10 — /scout route.
 *
 * Full-height mobile page that hosts:
 * - The multi-phase MobileScoutingForm
 * - Offline queue status bar (pending count + sync button)
 * - Success / queued confirmation screen
 * - Link back to full desktop observations page
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ClipboardCheck,
  CloudOff,
  RefreshCw,
  ArrowLeft,
  CheckCircle2,
  Clock,
} from 'lucide-react';
import { clsx } from 'clsx';
import MobileScoutingForm from '@/components/MobileScoutingForm';
import { useOfflineQueue } from '@/hooks/useOfflineQueue';
import { eventsQuery, teamsQuery } from '@/api/queries';
import type { Event, Team } from '@/types/models';

// ── Types ─────────────────────────────────────────────────────────────────────

type ScreenState = 'form' | 'success-online' | 'success-offline';

// ── Page ──────────────────────────────────────────────────────────────────────

export default function MobileScoutPage() {
  const [screen, setScreen] = useState<ScreenState>('form');

  const offlineQueue = useOfflineQueue();

  // Fetch events and teams — stale data is fine while offline (cached by RQ)
  const eventsResult = useQuery<Event[]>(eventsQuery());
  const teamsResult  = useQuery<Team[]>(teamsQuery());

  const events = eventsResult.data ?? [];
  const teams  = teamsResult.data  ?? [];

  // ── Handlers ───────────────────────────────────────────────────────────────

  const handleSuccess = (queued: boolean) => {
    setScreen(queued ? 'success-offline' : 'success-online');
  };

  const handleScoutAnother = () => setScreen('form');

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-screen max-h-screen bg-app-bg overflow-hidden">

      {/* Header */}
      <header className="flex items-center gap-3 px-4 py-3 bg-app-sidebar border-b border-app-border flex-shrink-0">
        <Link
          to="/"
          className="text-slate-500 hover:text-slate-300 transition-colors"
          aria-label="Back to dashboard"
        >
          <ArrowLeft size={20} />
        </Link>
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <div className="w-6 h-6 rounded-md bg-brand flex items-center justify-center flex-shrink-0">
            <ClipboardCheck size={13} className="text-white" />
          </div>
          <span className="text-sm font-semibold text-white truncate">Scout a Match</span>
        </div>

        {/* Queue badge */}
        {offlineQueue.pendingCount > 0 && (
          <button
            onClick={() => offlineQueue.syncNow()}
            disabled={offlineQueue.isSyncing}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-500/15 border border-amber-500/30 text-amber-400 text-xs font-medium active:scale-95 transition-transform"
            aria-label="Sync offline observations"
          >
            {offlineQueue.isSyncing ? (
              <RefreshCw size={11} className="animate-spin" />
            ) : (
              <CloudOff size={11} />
            )}
            {offlineQueue.pendingCount} pending
          </button>
        )}
      </header>

      {/* Body */}
      <div className="flex-1 min-h-0 overflow-hidden">

        {screen === 'form' && (
          <MobileScoutingForm
            events={events}
            teams={teams}
            onSubmit={offlineQueue.enqueueObservation}
            onSuccess={handleSuccess}
          />
        )}

        {(screen === 'success-online' || screen === 'success-offline') && (
          <SuccessScreen
            queued={screen === 'success-offline'}
            pendingCount={offlineQueue.pendingCount}
            isSyncing={offlineQueue.isSyncing}
            onSyncNow={offlineQueue.syncNow}
            onScoutAnother={handleScoutAnother}
          />
        )}
      </div>
    </div>
  );
}

// ── Success Screen ────────────────────────────────────────────────────────────

function SuccessScreen({
  queued,
  pendingCount,
  isSyncing,
  onSyncNow,
  onScoutAnother,
}: {
  queued:          boolean;
  pendingCount:    number;
  isSyncing:       boolean;
  onSyncNow:       () => void;
  onScoutAnother:  () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center h-full px-6 text-center gap-6">

      {/* Icon */}
      <div className={clsx(
        'w-20 h-20 rounded-full flex items-center justify-center',
        queued ? 'bg-amber-500/15' : 'bg-green-500/15'
      )}>
        {queued
          ? <Clock size={36} className="text-amber-400" />
          : <CheckCircle2 size={36} className="text-green-400" />
        }
      </div>

      {/* Message */}
      <div>
        <h2 className="text-xl font-semibold text-white mb-2">
          {queued ? 'Saved Offline' : 'Submitted!'}
        </h2>
        <p className="text-sm text-slate-400 leading-relaxed">
          {queued
            ? `Your observation has been saved locally. It will be synced to the server automatically when you're back online.`
            : 'Your observation has been submitted to the server successfully.'
          }
        </p>
      </div>

      {/* Pending queue info */}
      {pendingCount > 0 && (
        <div className="w-full p-4 bg-amber-500/10 border border-amber-500/25 rounded-xl">
          <p className="text-amber-400 text-sm font-medium mb-3">
            {pendingCount} observation{pendingCount !== 1 ? 's' : ''} pending sync
          </p>
          <button
            onClick={onSyncNow}
            disabled={isSyncing}
            className="flex items-center justify-center gap-2 w-full py-2.5 bg-amber-500/20 border border-amber-500/40 rounded-lg text-amber-300 text-sm font-medium active:scale-95 transition-transform disabled:opacity-50"
          >
            <RefreshCw size={14} className={isSyncing ? 'animate-spin' : ''} />
            {isSyncing ? 'Syncing…' : 'Sync Now'}
          </button>
        </div>
      )}

      {/* Actions */}
      <div className="flex flex-col gap-3 w-full">
        <button
          onClick={onScoutAnother}
          className="w-full py-3.5 bg-brand text-white rounded-xl text-sm font-semibold active:bg-brand/85 transition-colors"
        >
          Scout Another Match
        </button>
        <Link
          to="/observations"
          className="w-full py-3.5 border border-app-border rounded-xl text-slate-400 text-sm font-medium text-center active:bg-app-card transition-colors"
        >
          View All Observations
        </Link>
      </div>
    </div>
  );
}