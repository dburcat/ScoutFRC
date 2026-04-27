import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CalendarDays, MapPin, Users, ChevronRight, Search, Layers } from 'lucide-react';
import { type Event, type Team, type Match } from '@/types/models';
import {
  eventsQuery,
  eventTeamsQuery,
  eventMatchesQuery,
  CURRENT_YEAR,
} from '@/api/queries';
import { clsx } from 'clsx';

// ── Live indicator ──────────────────────────────────────────────────────────────
function LiveIndicator({ isFetching }: { isFetching: boolean }) {
  return (
    <div className="flex items-center gap-1.5">
      <div className={clsx(
        'w-1.5 h-1.5 rounded-full transition-colors',
        isFetching ? 'bg-brand animate-pulse' : 'bg-green-500'
      )} />
      <span className="text-[11px] text-slate-600">
        {isFetching ? 'Updating…' : 'Live'}
      </span>
    </div>
  );
}

// ── Helpers ─────────────────────────────────────────────────────────────────────
function eventStatus(event: Event): 'upcoming' | 'in-progress' | 'complete' {
  const now = new Date();
  const start = new Date(event.start_date);
  const end = new Date(event.end_date);
  end.setDate(end.getDate() + 1);
  if (now < start) return 'upcoming';
  if (now > end) return 'complete';
  return 'in-progress';
}

function fmtDate(d: string) {
  return new Date(d + 'T00:00:00').toLocaleDateString('en-US', {
    month: 'short', day: 'numeric',
  });
}

// ── Badges ──────────────────────────────────────────────────────────────────────
function StatusBadge({ status }: { status: ReturnType<typeof eventStatus> }) {
  return (
    <span className={clsx('text-[10px] font-medium px-2 py-0.5 rounded-full whitespace-nowrap', {
      'bg-brand/10 text-brand':           status === 'upcoming',
      'bg-amber-900/30 text-amber-400':   status === 'in-progress',
      'bg-green-900/30 text-green-400':   status === 'complete',
    })}>
      {status === 'in-progress' ? 'In progress'
        : status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

function MatchTypePill({ type }: { type: string }) {
  return (
    <span className={clsx('text-[10px] font-medium px-1.5 py-0.5 rounded', {
      'bg-slate-700/60 text-slate-400': type === 'qualification',
      'bg-amber-900/30 text-amber-400': type === 'semifinal',
      'bg-brand/10 text-brand':         type === 'final',
    })}>
      {type === 'qualification' ? 'Qual' : type === 'semifinal' ? 'SF' : 'Final'}
    </span>
  );
}

// ── Event list item ─────────────────────────────────────────────────────────────
function EventListItem({
  event, selected, onClick,
}: { event: Event; selected: boolean; onClick: () => void }) {
  const status = eventStatus(event);
  return (
    <button
      onClick={onClick}
      className={clsx(
        'flex items-center w-full text-left px-3 py-3 rounded-lg border transition-all gap-3',
        selected
          ? 'bg-brand/8 border-brand/40'
          : 'bg-app-card border-app-border hover:border-app-muted'
      )}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1 flex-wrap">
          <span className="text-[13px] font-medium text-white">{event.name}</span>
          <StatusBadge status={status} />
        </div>
        <div className="flex flex-wrap gap-x-3 gap-y-0.5">
          <span className="flex items-center gap-1 text-[11px] text-slate-500">
            <CalendarDays size={10} />
            {fmtDate(event.start_date)}–{fmtDate(event.end_date)}
          </span>
          {event.location && (
            <span className="flex items-center gap-1 text-[11px] text-slate-500">
              <MapPin size={10} />
              {event.location}
            </span>
          )}
          <span className="flex items-center gap-1 text-[11px] text-slate-500">
            <Layers size={10} />
            <span className="font-mono">{event.tba_event_key}</span>
          </span>
        </div>
      </div>
      <div className="flex items-center gap-3 flex-shrink-0">
        <div className="text-right hidden sm:block">
          <p className="text-[13px] font-medium text-white">{event.team_count || '—'}</p>
          <p className="text-[10px] text-slate-600">teams</p>
        </div>
        <div className="text-right hidden sm:block">
          <p className="text-[13px] font-medium text-white">{event.match_count || '—'}</p>
          <p className="text-[10px] text-slate-600">matches</p>
        </div>
        <ChevronRight size={14} className={clsx(
          'transition-colors', selected ? 'text-brand' : 'text-slate-700'
        )} />
      </div>
    </button>
  );
}

// ── Team table ──────────────────────────────────────────────────────────────────
function TeamTable({ teams, isFetching }: { teams: Team[]; isFetching: boolean }) {
  const navigate = useNavigate();
  
  if (teams.length === 0) return (
    <div className="text-center py-8">
      <Users size={20} className="text-slate-700 mx-auto mb-2" />
      <p className="text-slate-500 text-sm">No teams synced yet</p>
      <p className="text-slate-700 text-xs mt-1">
        The scheduler will populate this automatically
      </p>
    </div>
  );

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-left text-[10px] text-slate-600 border-b border-app-border">
            <th className="pb-2 font-medium pr-4 w-14">#</th>
            <th className="pb-2 font-medium pr-4">Team name</th>
            <th className="pb-2 font-medium pr-4 hidden sm:table-cell">School</th>
            <th className="pb-2 font-medium pr-4 hidden sm:table-cell">Location</th>
            <th className="pb-2 font-medium text-right">Rookie</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-app-border">
          {teams.map(team => (
            <tr
              key={team.team_id}
              onClick={() => navigate(`/teams/${team.team_id}`)}
              className={clsx(
                'transition-colors cursor-pointer',
                isFetching ? 'opacity-70' : 'hover:bg-app-card/50'
              )}
            >
              <td className="py-2 pr-4 font-mono font-medium text-white">
                {team.team_number}
              </td>
              <td className="py-2 pr-4 text-slate-300 font-medium">
                {team.team_name ?? '—'}
              </td>
              <td className="py-2 pr-4 text-slate-500 hidden sm:table-cell">
                {team.school_name ?? '—'}
              </td>
              <td className="py-2 pr-4 text-slate-500 hidden sm:table-cell">
                {[team.city, team.state_prov].filter(Boolean).join(', ') || '—'}
              </td>
              <td className="py-2 text-right text-slate-600">
                {team.rookie_year ?? '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Match table ─────────────────────────────────────────────────────────────────
function MatchTable({ matches, isFetching }: { matches: Match[]; isFetching: boolean }) {
  if (matches.length === 0) return (
    <div className="text-center py-8">
      <CalendarDays size={20} className="text-slate-700 mx-auto mb-2" />
      <p className="text-slate-500 text-sm">No matches synced yet</p>
      <p className="text-slate-700 text-xs mt-1">
        The scheduler will populate this automatically
      </p>
    </div>
  );

  const order: Record<string, number> = { qualification: 0, semifinal: 1, final: 2 };
  const sorted = [...matches].sort(
    (a, b) => order[a.match_type] - order[b.match_type] || a.match_number - b.match_number
  );

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-left text-[10px] text-slate-600 border-b border-app-border">
            <th className="pb-2 font-medium pr-3 w-12">#</th>
            <th className="pb-2 font-medium pr-3">Type</th>
            <th className="pb-2 font-medium pr-3">
              <span className="text-red-400">Red</span> score
            </th>
            <th className="pb-2 font-medium pr-3">
              <span className="text-blue-400">Blue</span> score
            </th>
            <th className="pb-2 font-medium pr-3 hidden sm:table-cell">Played</th>
            <th className="pb-2 font-medium text-right">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-app-border">
          {sorted.map(match => {
            const red  = match.alliances.find(a => a.color === 'red');
            const blue = match.alliances.find(a => a.color === 'blue');
            const playedAt = match.played_at
              ? new Date(match.played_at).toLocaleString('en-US', {
                  month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
                })
              : null;

            return (
              <tr
                key={match.match_id}
                className={clsx(
                  'transition-colors',
                  isFetching ? 'opacity-70' : 'hover:bg-app-card/50'
                )}
              >
                <td className="py-2 pr-3 font-mono font-medium text-white">
                  {match.match_number}
                </td>
                <td className="py-2 pr-3">
                  <MatchTypePill type={match.match_type} />
                </td>
                <td className="py-2 pr-3">
                  <span className={clsx('font-medium tabular-nums', {
                    'text-green-400': red?.won,
                    'text-red-400':   red?.won === false,
                    'text-slate-500': red?.total_score == null,
                  })}>
                    {red?.total_score ?? '—'}
                  </span>
                </td>
                <td className="py-2 pr-3">
                  <span className={clsx('font-medium tabular-nums', {
                    'text-green-400': blue?.won,
                    'text-blue-400':  blue?.won === false,
                    'text-slate-500': blue?.total_score == null,
                  })}>
                    {blue?.total_score ?? '—'}
                  </span>
                </td>
                <td className="py-2 pr-3 text-slate-500 hidden sm:table-cell">
                  {playedAt ?? '—'}
                </td>
                <td className="py-2 text-right">
                  <span className={clsx('text-[10px] px-1.5 py-0.5 rounded', {
                    'text-slate-500 bg-app-muted':    match.processing_status === 'pending',
                    'text-amber-400 bg-amber-900/20': match.processing_status === 'processing',
                    'text-green-400 bg-green-900/20': match.processing_status === 'complete',
                    'text-red-400 bg-red-900/20':     match.processing_status === 'failed',
                  })}>
                    {match.processing_status}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Detail panel ────────────────────────────────────────────────────────────────
type DetailTab = 'teams' | 'matches';

function EventDetailPanel({ event }: { event: Event }) {
  const [tab, setTab] = useState<DetailTab>('teams');

  const {
    data: teams = [],
    isLoading: teamsLoading,
    isFetching: teamsFetching,
  } = useQuery(eventTeamsQuery(event.event_id));

  const {
    data: matches = [],
    isLoading: matchesLoading,
    isFetching: matchesFetching,
  } = useQuery(eventMatchesQuery(event.event_id));

  const status = eventStatus(event);
  const isLoading = tab === 'teams' ? teamsLoading : matchesLoading;
  const isFetching = tab === 'teams' ? teamsFetching : matchesFetching;

  return (
    <div className="flex-1 min-w-0 bg-app-card border border-app-border rounded-xl overflow-hidden flex flex-col">
      {/* Header */}
      <div className="px-5 pt-5 pb-4 border-b border-app-border flex-shrink-0">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div>
            <h2 className="text-base font-medium text-white">{event.name}</h2>
            <p className="text-[11px] text-slate-600 font-mono mt-0.5">
              {event.tba_event_key}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <LiveIndicator isFetching={isFetching} />
            <StatusBadge status={status} />
          </div>
        </div>
        <div className="flex flex-wrap gap-x-4 gap-y-1">
          <span className="flex items-center gap-1.5 text-xs text-slate-500">
            <CalendarDays size={11} />
            {fmtDate(event.start_date)} – {fmtDate(event.end_date)}
          </span>
          {event.location && (
            <span className="flex items-center gap-1.5 text-xs text-slate-500">
              <MapPin size={11} />
              {event.location}
            </span>
          )}
          <span className="flex items-center gap-1.5 text-xs text-slate-500">
            <Users size={11} />
            {teams.length} teams · {matches.length} matches
          </span>
        </div>
      </div>

      {/* Sub-tabs */}
      <div className="flex border-b border-app-border flex-shrink-0">
        {(['teams', 'matches'] as DetailTab[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={clsx(
              'px-5 py-2.5 text-xs capitalize transition-colors border-b-2 -mb-px',
              tab === t
                ? 'text-brand border-brand font-medium'
                : 'text-slate-500 border-transparent hover:text-slate-300'
            )}
          >
            {t}
            <span className="ml-1.5 text-[10px] text-slate-600">
              {t === 'teams' ? teams.length : matches.length}
            </span>
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-5">
        {isLoading ? (
          <div className="space-y-2">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="h-8 bg-app-muted rounded animate-pulse" />
            ))}
          </div>
        ) : tab === 'teams' ? (
          <TeamTable teams={teams} isFetching={teamsFetching} />
        ) : (
          <MatchTable matches={matches} isFetching={matchesFetching} />
        )}
      </div>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────────
export default function EventsPage() {
  const [search, setSearch] = useState('');
  const [selectedEventId, setSelectedEventId] = useState<number | null>(null);

  const {
    data: events = [],
    isLoading,
    isFetching,
  } = useQuery(eventsQuery(CURRENT_YEAR));

  const filtered = events.filter(e =>
    e.name.toLowerCase().includes(search.toLowerCase()) ||
    e.tba_event_key.toLowerCase().includes(search.toLowerCase()) ||
    (e.location ?? '').toLowerCase().includes(search.toLowerCase())
  );

  const selectedEvent = events.find(e => e.event_id === selectedEventId) ?? null;

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Topbar */}
      <div className="flex items-center justify-between px-6 py-3.5 border-b border-app-border flex-shrink-0">
        <div>
          <p className="text-[15px] font-medium text-white">Events</p>
          <p className="text-[11px] text-slate-600 mt-0.5">
            {CURRENT_YEAR} season · {events.length} events
          </p>
        </div>
        <div className="flex items-center gap-3">
          <LiveIndicator isFetching={isFetching} />
          <div className="flex items-center gap-1.5 bg-app-card border border-app-border rounded-lg px-2.5 py-1.5 w-48">
            <Search size={11} className="text-slate-600 flex-shrink-0" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search events…"
              className="bg-transparent text-xs text-white placeholder:text-slate-600 outline-none w-full"
            />
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="flex flex-1 min-h-0 gap-4 p-5 overflow-hidden">
        {/* Event list */}
        <div className="w-80 flex-shrink-0 flex flex-col gap-2 overflow-y-auto pr-1">
          {isLoading ? (
            [...Array(5)].map((_, i) => (
              <div key={i} className="h-20 bg-app-card border border-app-border rounded-lg animate-pulse" />
            ))
          ) : filtered.length === 0 ? (
            <div className="bg-app-card border border-app-border rounded-xl p-6 text-center">
              <p className="text-slate-500 text-sm">No events found</p>
              <p className="text-slate-700 text-xs mt-1">
                {events.length === 0
                  ? 'Scheduler auto-populates events — or use TBA Sync in the sidebar'
                  : 'Try a different search'}
              </p>
            </div>
          ) : (
            filtered.map(event => (
              <EventListItem
                key={event.event_id}
                event={event}
                selected={event.event_id === selectedEventId}
                onClick={() =>
                  setSelectedEventId(prev =>
                    prev === event.event_id ? null : event.event_id
                  )
                }
              />
            ))
          )}
        </div>

        {/* Detail panel */}
        <div className="flex-1 min-w-0 flex flex-col">
          {selectedEvent ? (
            <EventDetailPanel event={selectedEvent} />
          ) : (
            <div className="flex-1 flex items-center justify-center border border-app-border rounded-xl border-dashed">
              <div className="text-center">
                <CalendarDays size={24} className="text-slate-700 mx-auto mb-2" />
                <p className="text-slate-500 text-sm">Select an event</p>
                <p className="text-slate-700 text-xs mt-1">
                  Click any event to view teams and matches
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}