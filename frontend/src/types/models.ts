export interface Event {
  event_id: number;
  tba_event_key: string;
  name: string;
  city: string | null;
  state_prov: string | null;
  country: string | null;
  start_date: string;
  end_date: string;
  season_year: number;
  perspective_matrix: object | null;
  created_at: string;
  location: string | null;
  team_count: number;
  match_count: number;
}

export interface Team {
  team_id: number;
  team_number: number;
  team_name: string | null;
  school_name: string | null;
  city: string | null;
  state_prov: string | null;
  country: string | null;
  rookie_year: number | null;
  created_at: string;
}

export interface Alliance {
  alliance_id: number;
  match_id: number;
  color: 'red' | 'blue';
  total_score: number | null;
  rp_earned: number | null;
  won: boolean | null;
}

export interface Match {
  match_id: number;
  event_id: number;
  tba_match_key: string;
  match_type: 'qualification' | 'semifinal' | 'final';
  match_number: number;
  video_url: string | null;
  processing_status: 'pending' | 'processing' | 'complete' | 'failed';
  played_at: string | null;
  created_at: string;
  alliances: Alliance[];
}

export interface SyncResult {
  status: string;
  event_key: string;
  teams_synced: number;
  matches_synced: number;
}