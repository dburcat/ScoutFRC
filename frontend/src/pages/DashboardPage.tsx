import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CalendarDays, MapPin, Users, ArrowRight } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { type Event, type Team } from '@/types/models';
import {
  eventsQuery,
  eventTeamsQuery,
  teamsQuery,
  CURRENT_YEAR,
} from '@/api/queries';
import { clsx } from 'clsx';

// ── Live pulse indicator ───────────────────────────────────────────────────────
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

// ── Stat Card ──────────────────────────────────────────────────────────────────
function StatCard({
  label, value, sub, loading,
}: {
  label: string; value: string | number; sub: string; loading?: boolean;
}) {
  return (
    <div className="bg-app-card border border-app-border rounded-xl p-4">
      <p className="text-[11px] text-slate-500 mb-1">{label}</p>
      {loading ? (
        <div className="h-7 w-16 bg-app-muted rounded animate-pulse mb-1" />
      ) : (
        <p className="text-2xl font-medium text-white leading-none mb-1">{value}</p>
      )}
      <p className="text-[11px] text-slate-600">{sub}</p>
    </div>
  );
}

// ── Event status helpers ───────────────────────────────────────────────────────
function eventStatus(event: Event): 'upcoming' | 'in-progress' | 'complete' {
  const now = new Date();
  const start = new Date(event.start_date);
  const end = new Date(event.end_date);
  end.setDate(end.getDate() + 1);
  if (now < start) return 'upcoming';
  if (now > end) return 'complete';
  return 'in-progress';
}

function StatusBadge({ status }: { status: ReturnType<typeof eventStatus> }) {
  return (
    <span className={clsx('text-[10px] font-medium px-2 py-0.5 rounded-full flex-shrink-0', {
      'bg-brand/10 text-brand':           status === 'upcoming',
      'bg-amber-900/30 text-amber-400':   status === 'in-progress',
      'bg-green-900/30 text-green-400':   status === 'complete',
    })}>
      {status === 'in-progress' ? 'In progress'
        : status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

// ── Sparkline ──────────────────────────────────────────────────────────────────
function Sparkline({ color = '#3b82f6' }: { color?: string }) {
  const points = [16, 12, 14, 8, 11, 6, 9].map((y, x) => `${x * 8},${y}`).join(' ');
  return (
    <svg width="48" height="20" viewBox="0 0 48 20" className="flex-shrink-0">
      <polyline points={points} fill="none" stroke={color} strokeWidth="1.5"
        strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// ── Team row ───────────────────────────────────────────────────────────────────
function TeamRow({
  team, selected, onClick,
}: { team: Team; selected: boolean; onClick: () => void }) {
  const loc = [team.city, team.state_prov].filter(Boolean).join(', ');
  return (
    <button
      onClick={onClick}
      className={clsx(
        'flex items-center w-full px-2.5 py-2 rounded-lg text-left transition-colors gap-2',
        selected ? 'bg-brand/8' : 'hover:bg-app-card'
      )}
    >
      <span className="text-[13px] font-medium text-white font-mono w-10 flex-shrink-0">
        {team.team_number}
      </span>
      <span className="text-xs text-slate-400 flex-1 truncate">
        {team.team_name ?? `Team ${team.team_number}`}
      </span>
      {loc && <span className="text-[11px] text-slate-600 flex-shrink-0 hidden sm:block">{loc}</span>}
      <Sparkline />
    </button>
  );
}

// ── Team detail panel ──────────────────────────────────────────────────────────
function TeamDetail({ team }: { team: Team }) {
  const name = team.team_name ?? `Team ${team.team_number}`;
  const initials = name.split(/\s+/).slice(0, 2).map(w => w[0]).join('').toUpperCase();

  return (
    <div className="w-48 flex-shrink-0 bg-app-card border border-app-border rounded-xl p-4">
      <div className="flex items-center gap-2.5 mb-4">
        <div className="w-9 h-9 rounded-full bg-brand/20 flex items-center justify-center text-[13px] font-medium text-brand flex-shrink-0">
          {initials}
        </div>
        <div className="min-w-0">
          <p className="text-lg font-medium text-white leading-none">{team.team_number}</p>
          <p className="text-xs text-slate-500 truncate mt-0.5">{name}</p>
        </div>
      </div>

      <div className="space-y-2.5 mb-3">
        {[
          { label: 'City',    value: team.city ?? '—' },
          { label: 'State',   value: team.state_prov ?? '—' },
          { label: 'Rookie',  value: team.rookie_year?.toString() ?? '—' },
        ].map(({ label, value }) => (
          <div key={label} className="flex justify-between items-center">
            <span className="text-[11px] text-slate-600">{label}</span>
            <span className="text-xs font-medium text-white">{value}</span>
          </div>
        ))}
      </div>

      {team.school_name && (
        <p className="text-[11px] text-slate-600 border-t border-app-border pt-3 mt-2">
          {team.school_name}
        </p>
      )}
      <p className="text-[10px] text-slate-700 mt-3">
        Match analytics available in Tier 6
      </p>
    </div>
  );
}

// ── Event Card ─────────────────────────────────────────────────────────────────
function EventCard({
  event, selected, onClick,
}: { event: Event; selected: boolean; onClick: () => void }) {
  const status = eventStatus(event);
  const fmt = (d: string) =>
    new Date(d + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

  return (
    <button
      onClick={onClick}
      className={clsx(
        'bg-app-card text-left rounded-xl p-4 border transition-all',
        selected
          ? 'border-brand/60 ring-1 ring-brand/20'
          : 'border-app-border hover:border-app-muted'
      )}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="min-w-0">
          <p className="text-[13px] font-medium text-white leading-snug">{event.name}</p>
          <p className="text-[11px] text-slate-600 font-mono mt-0.5">{event.tba_event_key}</p>
        </div>
        <StatusBadge status={status} />
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2">
        <span className="flex items-center gap-1 text-[11px] text-slate-500">
          <CalendarDays size={10} />
          {fmt(event.start_date)}–{fmt(event.end_date)}
        </span>
        {event.location && (
          <span className="flex items-center gap-1 text-[11px] text-slate-500">
            <MapPin size={10} />
            {event.location}
          </span>
        )}
        <span className="flex items-center gap-1 text-[11px] text-slate-500">
          <Users size={10} />
          {event.team_count > 0
            ? `${event.team_count} teams`
            : `${event.match_count} matches`}
        </span>
      </div>
    </button>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────────
type TabKey = 'events' | 'matches' | 'teams';

export default function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabKey>('events');
  const [selectedEventId, setSelectedEventId] = useState<number | null>(null);
  const [selectedTeamId, setSelectedTeamId] = useState<number | null>(null);
  const [eventSearch, setEventSearch] = useState('');

  const {
    data: events = [],
    isLoading: eventsLoading,
    isFetching: eventsFetching,
  } = useQuery(eventsQuery(CURRENT_YEAR));

  const { data: eventTeams = [] } = useQuery(eventTeamsQuery(selectedEventId));
  const { data: allTeams = [] }   = useQuery(teamsQuery());

  const filteredEvents = events.filter(e =>
    e.name.toLowerCase().includes(eventSearch.toLowerCase()) ||
    e.tba_event_key.toLowerCase().includes(eventSearch.toLowerCase())
  ).sort((a, b) => {
    const now = new Date();
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

  const selectedEvent = events.find(e => e.event_id === selectedEventId) ?? null;
  const selectedTeam  = (selectedEventId ? eventTeams : allTeams)
    .find(t => t.team_id === selectedTeamId) ?? null;
  const displayTeams  = selectedEventId ? eventTeams : allTeams;

  const totalMatches = events.reduce((a, e) => a + (e.match_count ?? 0), 0);

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Topbar */}
      <div className="flex items-center justify-between px-6 py-3.5 border-b border-app-border flex-shrink-0">
        <div>
          <p className="text-[15px] font-medium text-white">2025 Season Dashboard</p>
          <p className="text-[11px] text-slate-600 mt-0.5">Reefscape — active season</p>
        </div>
        <div className="flex items-center gap-3">
          <LiveIndicator isFetching={eventsFetching} />
          <span className="text-[11px] text-slate-600 bg-app-card border border-app-border px-2 py-1 rounded-lg">
            {user ? `Signed in as ${user.username}` : 'Viewing as guest'}
          </span>
        </div>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-5">
        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <StatCard
            label="Events tracked"
            value={events.length}
            sub={`${CURRENT_YEAR} season`}
            loading={eventsLoading}
          />
          <StatCard
            label="Teams indexed"
            value={allTeams.length || '—'}
            sub="via TBA sync"
            loading={eventsLoading}
          />
          <StatCard
            label="Matches logged"
            value={totalMatches || '—'}
            sub="across all events"
            loading={eventsLoading}
          />
          <StatCard
            label="Observations"
            value="—"
            sub="manual + CV"
          />
        </div>

        {/* Tabs */}
        <div className="flex gap-0.5 bg-app-card border border-app-border rounded-lg p-1 w-56">
          {(['events', 'matches', 'teams'] as TabKey[]).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={clsx(
                'flex-1 py-1 text-[11px] rounded-md capitalize transition-colors',
                activeTab === tab
                  ? 'bg-app-muted text-white font-medium'
                  : 'text-slate-500 hover:text-slate-300'
              )}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Events tab */}
        {activeTab === 'events' && (
          <>
            <div className="flex items-center justify-between">
              <p className="text-[13px] font-medium text-white">
                Upcoming &amp; recent events
              </p>
              <div className="flex items-center gap-1.5 bg-app-card border border-app-border rounded-lg px-2.5 py-1.5 w-44">
                <svg width="11" height="11" fill="none" viewBox="0 0 24 24" className="text-slate-600 flex-shrink-0">
                  <circle cx="11" cy="11" r="8" stroke="currentColor" strokeWidth="2" />
                  <path d="M21 21l-4.35-4.35" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
                <input
                  value={eventSearch}
                  onChange={e => setEventSearch(e.target.value)}
                  placeholder="Search events…"
                  className="bg-transparent text-xs text-white placeholder:text-slate-600 outline-none w-full"
                />
              </div>
            </div>

            {eventsLoading ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="bg-app-card border border-app-border rounded-xl p-4 h-24 animate-pulse" />
                ))}
              </div>
            ) : filteredEvents.length === 0 ? (
              <div className="bg-app-card border border-app-border rounded-xl p-8 text-center">
                <p className="text-slate-500 text-sm">No events found</p>
                <p className="text-slate-700 text-xs mt-1">
                  {events.length === 0
                    ? 'The scheduler will auto-populate events shortly, or use TBA Sync in the sidebar'
                    : 'Try a different search term'}
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {filteredEvents.map(event => (
                  <EventCard
                    key={event.event_id}
                    event={event}
                    selected={event.event_id === selectedEventId}
                    onClick={() => {
                      setSelectedEventId(prev =>
                        prev === event.event_id ? null : event.event_id
                      );
                      setSelectedTeamId(null);
                    }}
                  />
                ))}
              </div>
            )}

            {/* Teams panel */}
            {selectedEventId && (
              <>
                <div className="h-px bg-app-border" />
                <div className="flex items-center justify-between">
                  <p className="text-[13px] font-medium text-white">
                    Teams at {selectedEvent?.name}
                    <span className="text-slate-600 font-normal ml-1">
                      · {eventTeams.length} teams
                    </span>
                  </p>
                  <button
                    onClick={() => navigate('/events')}
                    className="flex items-center gap-1 text-[11px] text-brand hover:text-brand-300 transition-colors"
                  >
                    Full view <ArrowRight size={11} />
                  </button>
                </div>

                {eventTeams.length === 0 ? (
                  <p className="text-slate-600 text-xs">
                    No teams synced for this event yet — scheduler will update automatically.
                  </p>
                ) : (
                  <div className="flex gap-3">
                    <div className="flex-1 min-w-0 space-y-0.5">
                      {eventTeams.slice(0, 8).map(team => (
                        <TeamRow
                          key={team.team_id}
                          team={team}
                          selected={team.team_id === selectedTeamId}
                          onClick={() =>
                            setSelectedTeamId(prev =>
                              prev === team.team_id ? null : team.team_id
                            )
                          }
                        />
                      ))}
                      {eventTeams.length > 8 && (
                        <p className="text-[11px] text-slate-600 px-2.5 pt-1">
                          +{eventTeams.length - 8} more — see Full view
                        </p>
                      )}
                    </div>
                    {selectedTeam && <TeamDetail team={selectedTeam} />}
                  </div>
                )}
              </>
            )}
          </>
        )}

        {activeTab !== 'events' && (
          <div className="bg-app-card border border-app-border rounded-xl p-10 text-center">
            <p className="text-slate-500 text-sm capitalize">{activeTab} view</p>
            <p className="text-slate-700 text-xs mt-1">Coming in Tier 6</p>
          </div>
        )}
      </div>
    </div>
  );
}