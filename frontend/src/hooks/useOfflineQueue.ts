/**
 * useOfflineQueue.ts
 * ==================
 * Phase 2 Tier 10 — React hook that manages the offline observation queue.
 *
 * Responsibilities
 * ----------------
 * - Exposes queue state (pendingCount, items, isSyncing)
 * - Provides enqueueObservation() to save offline
 * - Auto-syncs when the device comes back online
 * - Exposes syncNow() for manual trigger
 * - Broadcasts a toast on sync completion
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import api from '@/api/client';
import { useNetworkStatus } from '@/hooks/useNetworkStatus';
import {
  enqueue,
  getAllItems,
  getPendingItems,
  markSyncing,
  markSynced,
  markFailed,
  removeItem,
  type ObservationPayload,
  type QueueItem,
} from '@/services/offlineQueue';

// ── Types ─────────────────────────────────────────────────────────────────────

export interface OfflineQueueState {
  items:        QueueItem[];
  pendingCount: number;
  isSyncing:    boolean;
  lastSyncAt:   Date | null;
}

export interface UseOfflineQueueReturn extends OfflineQueueState {
  enqueueObservation: (payload: ObservationPayload) => Promise<{ id: number; queued: boolean }>;
  syncNow:            () => Promise<void>;
  dismissItem:        (id: number) => Promise<void>;
  refresh:            () => Promise<void>;
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useOfflineQueue(): UseOfflineQueueReturn {
  const { isOnline } = useNetworkStatus();

  const [items,        setItems]       = useState<QueueItem[]>([]);
  const [pendingCount, setPendingCount] = useState(0);
  const [isSyncing,    setIsSyncing]   = useState(false);
  const [lastSyncAt,   setLastSyncAt]  = useState<Date | null>(null);

  const syncingRef = useRef(false); // prevent concurrent syncs

  // ── Load queue state ───────────────────────────────────────────────────────

  const refresh = useCallback(async () => {
    const all     = await getAllItems();
    const pending = await getPendingItems();
    setItems(all);
    setPendingCount(pending.length);
  }, []);

  // Initial load
  useEffect(() => { refresh(); }, [refresh]);

  // ── Sync engine ────────────────────────────────────────────────────────────

  const syncNow = useCallback(async () => {
    if (syncingRef.current || !isOnline) return;
    syncingRef.current = true;
    setIsSyncing(true);

    try {
      const pending = await getPendingItems();
      if (pending.length === 0) return;

      let successCount = 0;

      for (const item of pending) {
        const id = item.id!;
        await markSyncing(id);

        try {
          // POST to the scouting-observations endpoint
          await api.post('/scouting-observations/', {
            ...item.payload,
            is_offline: true,
          });
          await markSynced(id);
          successCount++;
        } catch (err: unknown) {
          const msg =
            err instanceof Error
              ? err.message
              : typeof err === 'object' && err !== null && 'response' in err
              ? String((err as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? 'Server error')
              : 'Unknown error';
          await markFailed(id, msg);
        }
      }

      setLastSyncAt(new Date());
      if (successCount > 0) {
        dispatchSyncEvent(successCount);
      }
    } finally {
      syncingRef.current = false;
      setIsSyncing(false);
      await refresh();
    }
  }, [isOnline, refresh]);

  // Auto-sync when coming back online
  useEffect(() => {
    if (isOnline) {
      syncNow();
    }
  }, [isOnline, syncNow]);

  // Poll queue state every 30s when online (keeps badge count fresh)
  useEffect(() => {
    const interval = setInterval(() => {
      refresh();
      if (isOnline) syncNow();
    }, 30_000);
    return () => clearInterval(interval);
  }, [isOnline, refresh, syncNow]);

  // ── Public actions ─────────────────────────────────────────────────────────

  /**
   * Save an observation. If online, POSTs immediately.
   * If offline (or POST fails), saves to IndexedDB queue.
   * Returns { id, queued: true } if saved to queue, { id, queued: false } if sent directly.
   */
  const enqueueObservation = useCallback(
    async (payload: ObservationPayload): Promise<{ id: number; queued: boolean }> => {
      if (isOnline) {
        try {
          const res = await api.post<{ observation_id: number }>(
            '/scouting-observations/',
            { ...payload, is_offline: false }
          );
          return { id: res.data.observation_id, queued: false };
        } catch {
          // Fall through to offline queue
        }
      }

      // Offline path — save to IndexedDB
      const id = await enqueue({ ...payload, is_offline: true });
      await refresh();
      return { id, queued: true };
    },
    [isOnline, refresh]
  );

  const dismissItem = useCallback(async (id: number) => {
    await removeItem(id);
    await refresh();
  }, [refresh]);

  return {
    items,
    pendingCount,
    isSyncing,
    lastSyncAt,
    enqueueObservation,
    syncNow,
    dismissItem,
    refresh,
  };
}

// ── Sync event (consumed by toast in App.tsx) ─────────────────────────────────

function dispatchSyncEvent(count: number) {
  window.dispatchEvent(
    new CustomEvent('offline-sync-complete', { detail: { count } })
  );
}