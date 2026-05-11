import { useQuery } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
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
  const navigate = useNavigate();

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
                onClick={() => navigate(`/matches/${match.match_id}`)}
                className={clsx(
                  'transition-colors cursor-pointer',
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
  const [tab, setTab] = useState<DetailTab>('matches');
  const contentRef = useRef<HTMLDivElement | null>(null);

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

  useEffect(() => {
    setTimeout(() => {
      contentRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
    }, 150);
  }, [event.event_id, tab]);

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
            {matches.length} matches · {teams.length} teams
          </span>
        </div>
      </div>

      {/* Sub-tabs */}
      <div className="flex border-b border-app-border flex-shrink-0">
        {(['matches', 'teams'] as DetailTab[]).map(t => (
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
              {t === 'matches' ? matches.length : teams.length}
            </span>
          </button>
        ))}
      </div>

      {/* Content */}
      <div ref={contentRef} className="flex-1 overflow-y-auto p-5">
        {isLoading ? (
          <div className="space-y-2">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="h-8 bg-app-muted rounded animate-pulse" />
            ))}
          </div>
        ) : tab === 'matches' ? (
          <MatchTable matches={matches} isFetching={matchesFetching} />
        ) : (
          <TeamTable teams={teams} isFetching={teamsFetching} />
        )}
      </div>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────────
export default function EventsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState('');
  const detailPanelRef = useRef<HTMLDivElement | null>(null);
  const [selectedEventId, setSelectedEventId] = useState<number | null>(
    (() => {
      const eventId = searchParams.get('eventId');
      return eventId ? Number(eventId) : null;
    })()
  );
  const [selectedYear, setSelectedYear] = useState(() => {
    const year = searchParams.get('year');
    const parsedYear = year ? Number(year) : CURRENT_YEAR;
    return Number.isFinite(parsedYear) ? parsedYear : CURRENT_YEAR;
  });

  // Generate years from 2009 to CURRENT_YEAR
  const years = Array.from(
    { length: CURRENT_YEAR - 2009 + 1 },
    (_, i) => CURRENT_YEAR - i
  );

  const {
    data: events = [],
    isLoading,
    isFetching,
  } = useQuery(eventsQuery(selectedYear));

  const filtered = events.filter(e =>
    e.name.toLowerCase().includes(search.toLowerCase()) ||
    e.tba_event_key.toLowerCase().includes(search.toLowerCase()) ||
    (e.location ?? '').toLowerCase().includes(search.toLowerCase())
  ).sort((a, b) => {
    const aStart = new Date(a.start_date);
    const aEnd = new Date(a.end_date);
    const bStart = new Date(b.start_date);
    const bEnd = new Date(b.end_date);

    // Determine status for each event
    const aStatus = eventStatus(a);
    const bStatus = eventStatus(b);

    // Priority: in-progress > upcoming > complete
    const statusOrder = { 'in-progress': 0, 'upcoming': 1, 'complete': 2 };
    if (statusOrder[aStatus] !== statusOrder[bStatus]) {
      return statusOrder[aStatus] - statusOrder[bStatus];
    }

    // Within same status, sort by proximity to today
    if (aStatus === 'in-progress') {
      // In-progress: sort by how far into the event (closer to start = higher priority)
      return aStart.getTime() - bStart.getTime();
    } else if (aStatus === 'upcoming') {
      // Upcoming: sort by start date (closest to today first)
      return aStart.getTime() - bStart.getTime();
    } else {
      // Complete: sort by end date (most recent first)
      return bEnd.getTime() - aEnd.getTime();
    }
  });

  const updateUrlState = (year: number, eventId: number | null) => {
    const params = new URLSearchParams(searchParams);
    params.set('year', String(year));
    if (eventId === null) {
      params.delete('eventId');
    } else {
      params.set('eventId', String(eventId));
    }
    setSearchParams(params, { replace: true });
  };

  const selectedEvent = events.find(e => e.event_id === selectedEventId) ?? null;



useEffect(() => {
  if (selectedEvent && detailPanelRef.current) {
    const targetPos = detailPanelRef.current.getBoundingClientRect().top + window.pageYOffset;
    const startPos = window.pageYOffset;
    const distance = targetPos - startPos;
    const duration = 1500; // 1.5 seconds - change this to slow it down!
    let start = null;

    function step(timestamp) {
      if (!start) start = timestamp;
      const progress = timestamp - start;
      
      // Easing function: make it feel natural
      const easeInOutQuad = (t) => t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
      const percentage = Math.min(progress / duration, 1);
      
      window.scrollTo(0, startPos + distance * easeInOutQuad(percentage));

      if (progress < duration) {
        window.requestAnimationFrame(step);
      }
    }

    window.requestAnimationFrame(step);
  }
}, [selectedEvent]);

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Topbar */}
      <div className="flex items-center justify-between px-6 py-3.5 border-b border-app-border flex-shrink-0">
        <div>
          <p className="text-[15px] font-medium text-white">Events</p>
          <div className="flex items-center gap-2 mt-0.5">
            <select
              value={selectedYear}
              onChange={(e) => {
                const nextYear = Number(e.target.value);
                setSelectedYear(nextYear);
                setSelectedEventId(null); // Clear selection when year changes
                updateUrlState(nextYear, null);
              }}
              className="bg-app-card border border-app-border rounded px-2 py-1 text-xs text-white cursor-pointer hover:border-app-muted focus:outline-none focus:ring-1 focus:ring-brand"
            >
              {years.map(year => (
                <option key={year} value={year}>
                  {year}
                </option>
              ))}
            </select>
            <span className="text-[11px] text-slate-600">
              · {events.length} events
            </span>
          </div>
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
                onClick={() => {
                  setSelectedEventId(prev => {
                    const nextEventId = prev === event.event_id ? null : event.event_id;
                    updateUrlState(selectedYear, nextEventId);
                    return nextEventId;
                  });
                }}
              />
            ))
          )}
        </div>

        {/* Detail panel */}
        <div ref={detailPanelRef} className="flex-1 min-w-0 flex flex-col">
          {selectedEvent ? (
            <EventDetailPanel event={selectedEvent} />
          ) : (
            <div className="flex-1 flex flex-col items-center justify-start pt-10 border border-app-border rounded-xl border-dashed gap-4">
              <svg width="320" height="200" viewBox="200 130 280 160" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" className="opacity-[0.06]">
                <polygon points="340,140 400,174 400,242 340,276 280,242 280,174" fill="none" stroke="#ffffff" strokeWidth="2.5"/>
                <line x1="400" y1="174" x2="440" y2="155" stroke="#ffffff" strokeWidth="1.5"/>
                <line x1="440" y1="155" x2="462" y2="155" stroke="#ffffff" strokeWidth="1.5"/>
                <circle cx="462" cy="155" r="3" fill="#ffffff"/>
                <line x1="400" y1="242" x2="440" y2="261" stroke="#ffffff" strokeWidth="1.5"/>
                <line x1="440" y1="261" x2="462" y2="261" stroke="#ffffff" strokeWidth="1.5"/>
                <circle cx="462" cy="261" r="3" fill="#ffffff"/>
                <line x1="280" y1="174" x2="240" y2="155" stroke="#ffffff" strokeWidth="1.5"/>
                <line x1="240" y1="155" x2="218" y2="155" stroke="#ffffff" strokeWidth="1.5"/>
                <circle cx="218" cy="155" r="3" fill="#ffffff"/>
                <line x1="280" y1="242" x2="240" y2="261" stroke="#ffffff" strokeWidth="1.5"/>
                <line x1="240" y1="261" x2="218" y2="261" stroke="#ffffff" strokeWidth="1.5"/>
                <circle cx="218" cy="261" r="3" fill="#ffffff"/>
                <line x1="340" y1="140" x2="340" y2="118" stroke="#ffffff" strokeWidth="1.5"/>
                <circle cx="340" cy="118" r="3" fill="#ffffff"/>
                <line x1="340" y1="276" x2="340" y2="298" stroke="#ffffff" strokeWidth="1.5"/>
                <circle cx="340" cy="298" r="3" fill="#ffffff"/>
                <line x1="295" y1="248" x2="385" y2="248" stroke="#ffffff" strokeWidth="1.5" strokeLinecap="round"/>
                <rect x="298" y="234" width="12" height="14" rx="2" fill="#ffffff"/>
                <rect x="314" y="224" width="12" height="24" rx="2" fill="#ffffff"/>
                <rect x="330" y="216" width="12" height="32" rx="2" fill="#ffffff"/>
                <rect x="346" y="204" width="12" height="44" rx="2" fill="#ffffff"/>
                <rect x="362" y="192" width="12" height="56" rx="2" fill="#ffffff"/>
                <polyline points="304,231 320,221 336,213 352,201 368,189" stroke="#ffffff" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
                <circle cx="368" cy="189" r="4" fill="#ffffff"/>
              </svg>
              <div className="text-center">
                <p className="text-slate-600 text-sm">Select an event to get started</p>
                <p className="text-slate-700 text-xs mt-1">View teams and matches, then click a match for the full breakdown</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}