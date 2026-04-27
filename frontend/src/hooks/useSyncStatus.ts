import { useQuery } from '@tanstack/react-query';
import api from '@/api/client';

export interface SyncStatus {
  events_count: number;
  teams_count: number;
  active_event_count: number;
  upcoming_event_count: number;
  last_sync: string | null;
  scheduler_running: boolean;
  error?: string;
}

/**
 * Hook to check automatic sync status from the backend.
 * Polls every 3 seconds while scheduler is running and has data.
 * No authentication required — available to all users including guests.
 */
export function useSyncStatus() {
  return useQuery<SyncStatus>({
    queryKey: ['syncStatus'],
    queryFn: async () => {
      const response = await api.get<SyncStatus>('/admin/sync/status');
      return response.data;
    },
    refetchInterval: (query) => {
      // If scheduler is running and we have events, refetch every 3 seconds
      // Otherwise, check less frequently (30 seconds)
      if (query.state.data?.scheduler_running && query.state.data?.events_count > 0) {
        return 3000; // 3 second poll while active
      }
      return 30000; // 30 second poll otherwise
    },
    staleTime: 2000, // Data is fresh for 2 seconds
  });
}
