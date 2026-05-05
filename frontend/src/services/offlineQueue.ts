/**
 * offlineQueue.ts
 * ===============
 * Phase 2 Tier 10 — Offline-first scouting observation queue.
 *
 * Uses IndexedDB (via `idb`) to persist scouting observations when the
 * device is offline. When connectivity is restored, useOfflineQueue drains
 * the queue by POSTing each entry to the backend API.
 *
 * Schema
 * ------
 * DB name:    scouterfrc
 * Version:    1
 * Store:      offline_observations
 *   id        — auto-increment key
 *   payload   — the full observation POST body (mirrors /scouting-observations/)
 *   createdAt — ISO timestamp
 *   status    — 'pending' | 'syncing' | 'failed'
 *   attempts  — number of sync attempts
 *   error     — last error message if status === 'failed'
 */

import { openDB, type IDBPDatabase } from 'idb';

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ObservationPayload {
  match_id:      number | null;
  team_id:       number | null;
  team_number:   number;
  event_id:      number | null;
  score:         number | null;
  rating:        number;
  notes:         string;
  auto_notes:    string;
  teleop_notes:  string;
  endgame_notes: string;
  is_offline:    boolean;  // always true when queued
}

export type QueueItemStatus = 'pending' | 'syncing' | 'failed';

export interface QueueItem {
  id?:       number;          // set by IndexedDB
  payload:   ObservationPayload;
  createdAt: string;          // ISO string
  status:    QueueItemStatus;
  attempts:  number;
  error?:    string;
}

// ── DB setup ──────────────────────────────────────────────────────────────────

const DB_NAME    = 'scouterfrc';
const DB_VERSION = 1;
const STORE      = 'offline_observations';
const MAX_ATTEMPTS = 3;

let _db: IDBPDatabase | null = null;

async function getDB(): Promise<IDBPDatabase> {
  if (_db) return _db;
  _db = await openDB(DB_NAME, DB_VERSION, {
    upgrade(db: IDBPDatabase) {
      if (!db.objectStoreNames.contains(STORE)) {
        const store = db.createObjectStore(STORE, {
          keyPath:       'id',
          autoIncrement: true,
        });
        store.createIndex('status',    'status',    { unique: false });
        store.createIndex('createdAt', 'createdAt', { unique: false });
      }
    },
  });
  return _db;
}

// ── Public API ────────────────────────────────────────────────────────────────

/** Add a new observation to the offline queue. Returns the assigned id. */
export async function enqueue(payload: ObservationPayload): Promise<number> {
  const db = await getDB();
  const item: QueueItem = {
    payload,
    createdAt: new Date().toISOString(),
    status:    'pending',
    attempts:  0,
  };
  const id = await db.add(STORE, item);
  return id as number;
}

/** Return all items in the queue, newest first. */
export async function getAllItems(): Promise<QueueItem[]> {
  const db = await getDB();
  const all = (await db.getAll(STORE)) as QueueItem[];
  return all.sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
  );
}

/** Return only pending items (not yet attempted or previously failed but retryable). */
export async function getPendingItems(): Promise<QueueItem[]> {
  const db    = await getDB();
  const index = db.transaction(STORE).store.index('status');
  const pending = (await index.getAll('pending')) as QueueItem[];
  // Also retry failed items that haven't exceeded MAX_ATTEMPTS
  const failed  = (await index.getAll('failed')) as QueueItem[];
  const retryable = failed.filter(item => (item.attempts ?? 0) < MAX_ATTEMPTS);
  return [...pending, ...retryable];
}

/** Count of pending + retryable items. */
export async function getPendingCount(): Promise<number> {
  const items = await getPendingItems();
  return items.length;
}

/** Mark an item as syncing. */
export async function markSyncing(id: number): Promise<void> {
  const db   = await getDB();
  const item = (await db.get(STORE, id)) as QueueItem | undefined;
  if (!item) return;
  await db.put(STORE, { ...item, status: 'syncing', id });
}

/** Mark an item as successfully synced — removes it from the queue. */
export async function markSynced(id: number): Promise<void> {
  const db = await getDB();
  await db.delete(STORE, id);
}

/** Mark an item as failed, incrementing the attempt counter. */
export async function markFailed(id: number, error: string): Promise<void> {
  const db   = await getDB();
  const item = (await db.get(STORE, id)) as QueueItem | undefined;
  if (!item) return;
  await db.put(STORE, {
    ...item,
    id,
    status:   'failed',
    attempts: (item.attempts ?? 0) + 1,
    error,
  });
}

/** Permanently delete a specific item (e.g. user manually dismisses it). */
export async function removeItem(id: number): Promise<void> {
  const db = await getDB();
  await db.delete(STORE, id);
}

/** Clear all items from the queue (used in tests / reset). */
export async function clearQueue(): Promise<void> {
  const db = await getDB();
  await db.clear(STORE);
}