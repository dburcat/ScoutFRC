// src/api/queries.ts
// Central query definitions for all TBA-backed data.
// refetchInterval keeps the UI in sync with the backend scheduler:
//   - Events/teams: every 30s  (roster/schedule changes)
//   - Matches:      every 30s during live events, fine for other views too
//   - Stats:        every 60s  (heavier to compute)
//
// TanStack Query deduplicates — multiple components using the same
// queryKey share one network request and one cache entry.

import api from '@/api/client';
import type { Event, Team, Match } from '@/types/models';

export const CURRENT_YEAR = new Date().getFullYear();

// How often each data type polls the backend (ms)
const INTERVAL = {
  events:  30_000,   // 30s
  matches: 30_000,   // 30s
  teams:   60_000,   // 60s
} as const;

// ── Events ─────────────────────────────────────────────────────────────────
export const eventsQuery = (year = CURRENT_YEAR) => ({
  queryKey: ['events', year] as const,
  queryFn:  () => api.get<Event[]>(`/events/?year=${year}`).then(r => r.data),
  refetchInterval: INTERVAL.events,
  staleTime: 20_000,
});

export const eventQuery = (eventId: number) => ({
  queryKey: ['event', eventId] as const,
  queryFn:  () => api.get<Event>(`/events/${eventId}`).then(r => r.data),
  refetchInterval: INTERVAL.events,
  staleTime: 20_000,
  enabled: !!eventId,
});

// ── Teams ──────────────────────────────────────────────────────────────────
export const teamsQuery = () => ({
  queryKey: ['teams'] as const,
  queryFn:  () => api.get<Team[]>('/teams/').then(r => r.data),
  refetchInterval: INTERVAL.teams,
  staleTime: 45_000,
});

export const eventTeamsQuery = (eventId: number | null) => ({
  queryKey: ['event-teams', eventId] as const,
  queryFn:  () => api.get<Team[]>(`/events/${eventId}/teams`).then(r => r.data),
  refetchInterval: INTERVAL.teams,
  staleTime: 45_000,
  enabled: !!eventId,
});

// ── Matches ────────────────────────────────────────────────────────────────
export const eventMatchesQuery = (eventId: number | null) => ({
  queryKey: ['event-matches', eventId] as const,
  queryFn:  () => api.get<Match[]>(`/events/${eventId}/matches`).then(r => r.data),
  refetchInterval: INTERVAL.matches,
  staleTime: 20_000,
  enabled: !!eventId,
});

export const teamMatchesQuery = (teamId: number | null) => ({
  queryKey: ['team-matches', teamId] as const,
  queryFn:  () => api.get<Match[]>(`/teams/${teamId}/matches`).then(r => r.data),
  refetchInterval: INTERVAL.matches,
  staleTime: 20_000,
  enabled: !!teamId,
});

// ── User Alliances ─────────────────────────────────────────────────────────
export const userAlliancesQuery = () => ({
  queryKey: ['user-alliances'] as const,
  queryFn:  () => api.get('/user_alliances/my-alliances').then(r => r.data),
  refetchInterval: 60_000,
  staleTime: 45_000,
});

// ── Scouting Observations ──────────────────────────────────────────────────
export const scoutingObservationsQuery = () => ({
  queryKey: ['scouting-observations'] as const,
  queryFn:  () => api.get('/scouting_observations/').then(r => r.data),
  refetchInterval: 60_000,
  staleTime: 45_000,
});