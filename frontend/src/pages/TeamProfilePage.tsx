import { useQuery } from '@tanstack/react-query';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useMemo, useState, useEffect } from 'react';
import {
  ArrowLeft, Trophy, TrendingUp, Calendar, Target,
  ChevronDown, Swords, Star,
} from 'lucide-react';
import {
  BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts';
import { type Team, type Match, type Event } from '@/types/models';
import { teamQuery, teamMatchesQuery } from '@/api/queries';
import { clsx } from 'clsx';

// ── Tooltip style shared across charts ────────────────────────────────────────
const TOOLTIP_STYLE = {
  contentStyle: {
    backgroundColor: '#1e293b',
    border: '1px solid #475569',
    borderRadius: '0.5rem',
    color: '#fff',
    fontSize: '12px',
  },
};

// ── Year selector dropdown ─────────────────────────────────────────────────────
function YearSelector({
  years,
  selected,
  onChange,
}: {
  years: (number | 'all')[];
  selected: number | 'all';
  onChange: (y: number | 'all') => void;
}) {
  return (
    <div className="relative inline-block">
      <select
        value={selected === 'all' ? 'all' : selected}
        onChange={e => onChange(e.target.value === 'all' ? 'all' : parseInt(e.target.value))}
        className="appearance-none bg-app-card border border-app-border text-white text-xs font-medium
          rounded-lg pl-3 pr-7 py-1.5 outline-none cursor-pointer hover:border-brand/60 transition-colors"
      >
        {years.map(y => (
          <option key={y} value={y}>
            {y === 'all' ? 'All years' : String(y)}
          </option>
        ))}
      </select>
      <ChevronDown
        size={12}
        className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none"
      />
    </div>
  );
}

// ── Stat badge ────────────────────────────────────────────────────────────────
function StatBadge({
  label, value, icon, highlight,
}: {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  highlight?: boolean;
}) {
  return (
    <div className={clsx(
      'flex items-center gap-2 bg-app-card border rounded-lg px-3 py-2',
      highlight ? 'border-brand/40' : 'border-app-border'
    )}>
      <div className="text-brand flex-shrink-0">{icon}</div>
      <div>
        <p className="text-[10px] text-slate-600">{label}</p>
        <p className="text-sm font-medium text-white">{value}</p>
      </div>
    </div>
  );
}

// ── Match row ─────────────────────────────────────────────────────────────────
function MatchRow({ match, teamId }: { match: Match; teamId: number }) {
  const red  = match.alliances.find(a => a.color === 'red');
  const blue = match.alliances.find(a => a.color === 'blue');
  const teamAlliance = match.alliances.find(a =>
    a.robot_performances.some(rp => rp.team_id === teamId)
  );
  const won = teamAlliance?.won;

  return (
    <tr className="hover:bg-app-card/50 transition-colors border-b border-app-border last:border-0">
      <td className="py-2.5 px-4">
        <span className={clsx('text-[10px] font-medium px-1.5 py-0.5 rounded', {
          'bg-green-900/30 text-green-400': won === true,
          'bg-red-900/30 text-red-400':     won === false,
          'bg-slate-700/50 text-slate-500': won === null,
        })}>
          {won === true ? 'W' : won === false ? 'L' : '—'}
        </span>
      </td>
      <td className="py-2.5 px-4 text-white font-mono text-xs">{match.match_number}</td>
      <td className="py-2.5 px-4 text-slate-500 text-xs capitalize">
        {match.match_type === 'qualification' ? 'Qual'
          : match.match_type === 'semifinal' ? 'SF'
          : 'Final'}
      </td>
      <td className="py-2.5 px-4 text-center">
        <span className={clsx('text-xs font-medium', {
          'text-red-300 font-bold': red?.won,
          'text-red-400/60':        !red?.won,
        })}>
          {red?.total_score ?? '—'}
        </span>
      </td>
      <td className="py-2.5 px-4 text-center">
        <span className={clsx('text-xs font-medium', {
          'text-blue-300 font-bold': blue?.won,
          'text-blue-400/60':        !blue?.won,
        })}>
          {blue?.total_score ?? '—'}
        </span>
      </td>
      <td className="py-2.5 px-4 text-right">
        <Link
          to={`/matches/${match.match_id}`}
          className="text-[11px] text-brand hover:underline"
        >
          Details
        </Link>
      </td>
    </tr>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────────
export default function TeamProfilePage() {
  const { teamId } = useParams<{ teamId: string }>();
  const navigate = useNavigate();
  const teamIdNum = teamId ? parseInt(teamId) : null;

  const { data: team,    isLoading: teamLoading    } = useQuery(teamQuery(teamIdNum));
  const { data: matches = [], isLoading: matchesLoading } = useQuery(teamMatchesQuery(teamIdNum));

  // Fetch all events to build an event_id → season_year lookup map,
  // since match objects have event_id but not season_year directly.
  const { data: allEvents = [] } = useQuery({
    queryKey: ['events-all'],
    queryFn: async () => {
      const { default: api } = await import('@/api/client');
      const res = await api.get<Event[]>('/events/?limit=100000');
      return res.data;
    },
    staleTime: 5 * 60_000,
  });

  // Build event_id → season_year lookup
  const eventYearMap = useMemo(() => {
    const map = new Map<number, number>();
    allEvents.forEach(e => map.set(e.event_id, e.season_year));
    return map;
  }, [allEvents]);

  // Annotate matches with their year
  const matchesWithYear = useMemo(() =>
    matches.map(m => ({
      ...m,
      season_year: eventYearMap.get(m.event_id) ?? null,
    })),
    [matches, eventYearMap]
  );

  // Derive sorted list of years this team has data for
  const availableYears = useMemo(() => {
    const yrs = new Set<number>();
    matchesWithYear.forEach(m => { if (m.season_year) yrs.add(m.season_year); });
    return Array.from(yrs).sort((a, b) => b - a); // newest first
  }, [matchesWithYear]);

  // Default to latest year with data
  const [selectedYear, setSelectedYear] = useState<number | 'all' | null>(null);

  useEffect(() => {
    if (availableYears.length > 0 && selectedYear === null) {
      setSelectedYear(availableYears[0]); // latest year
    }
  }, [availableYears]);

  // Year selector options: all available years + "All years"
  const yearOptions: (number | 'all')[] = availableYears.length > 0
    ? [...availableYears, 'all']
    : ['all'];

  // Filter matches by selected year
  const filteredMatches = useMemo(() => {
    if (selectedYear === 'all' || selectedYear === null) return matchesWithYear;
    return matchesWithYear.filter(m => m.season_year === selectedYear);
  }, [matchesWithYear, selectedYear]);

  // ── Stats computed from filtered matches ──────────────────────────────────
  const stats = useMemo(() => {
    const total = filteredMatches.length;
    if (total === 0) return { total: 0, wins: 0, losses: 0, avgScore: 0, winRate: 0, highScore: 0 };

    let wins = 0, sumScore = 0, highScore = 0;
    filteredMatches.forEach(m => {
      const teamAlliance = m.alliances.find(a =>
        a.robot_performances.some(rp => rp.team_id === teamIdNum)
      );
      if (teamAlliance?.won) wins++;
      const score = teamAlliance?.total_score ?? 0;
      sumScore += score;
      if (score > highScore) highScore = score;
    });

    return {
      total,
      wins,
      losses: total - wins,
      avgScore: Math.round(sumScore / total),
      winRate: Math.round((wins / total) * 100),
      highScore,
    };
  }, [filteredMatches, teamIdNum]);

  // ── Chart data ────────────────────────────────────────────────────────────
  const chartData = useMemo(() => {
    return [...filteredMatches]
      .sort((a, b) => (a.match_number ?? 0) - (b.match_number ?? 0))
      .map(m => {
        const teamAlliance = m.alliances.find(a =>
          a.robot_performances.some(rp => rp.team_id === teamIdNum)
        );
        const rp = teamAlliance?.robot_performances.find(r => r.team_id === teamIdNum);
        return {
          match: m.match_number,
          allianceScore: teamAlliance?.total_score ?? 0,
          robotContrib: rp?.total_score_contribution ?? 0,
          auto: rp?.auto_score ?? 0,
          teleop: rp?.teleop_score ?? 0,
          endgame: rp?.endgame_score ?? 0,
          won: teamAlliance?.won ?? null,
          matchId: m.match_id,
        };
      });
  }, [filteredMatches, teamIdNum]);

  const avgLine = stats.avgScore;

  // ── Year breakdown (only for "all years" view) ───────────────────────────
  const yearBreakdown = useMemo(() => {
    if (selectedYear !== 'all') return [];
    return availableYears.map(yr => {
      const yrMatches = matchesWithYear.filter(m => m.season_year === yr);
      const total = yrMatches.length;
      let wins = 0, sumScore = 0;
      yrMatches.forEach(m => {
        const ta = m.alliances.find(a =>
          a.robot_performances.some(rp => rp.team_id === teamIdNum)
        );
        if (ta?.won) wins++;
        sumScore += ta?.total_score ?? 0;
      });
      return {
        year: yr,
        matches: total,
        wins,
        avgScore: total > 0 ? Math.round(sumScore / total) : 0,
        winRate: total > 0 ? Math.round((wins / total) * 100) : 0,
      };
    });
  }, [selectedYear, availableYears, matchesWithYear, teamIdNum]);

  if (!teamIdNum) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-slate-500">Team not found</p>
      </div>
    );
  }

  const isLoading = teamLoading || matchesLoading;

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Header */}
      <div className="px-6 py-3.5 border-b border-app-border flex-shrink-0 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(-1)}
            className="text-slate-500 hover:text-slate-300 transition-colors p-1"
          >
            <ArrowLeft size={18} />
          </button>
          <div>
            <p className="text-[15px] font-medium text-white">
              Team {team?.team_number ?? teamIdNum}
            </p>
            <p className="text-[11px] text-slate-600 mt-0.5">
              {team?.team_name
                ? `${team.team_name} · Robot performance profile`
                : 'Robot performance profile'}
            </p>
          </div>
        </div>

        {/* Year selector — shown once we know what years exist */}
        {!isLoading && availableYears.length > 0 && selectedYear !== null && (
          <YearSelector
            years={yearOptions}
            selected={selectedYear}
            onChange={setSelectedYear}
          />
        )}
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-6 space-y-5">

        {/* Team info strip */}
        {team && (
          <div className="flex flex-wrap gap-2 text-[11px] text-slate-500">
            {team.city && <span>{team.city}</span>}
            {team.state_prov && <><span>·</span><span>{team.state_prov}</span></>}
            {team.country && <><span>·</span><span>{team.country}</span></>}
            {team.rookie_year && <><span>·</span><span>Rookie {team.rookie_year}</span></>}
            {team.school_name && <><span>·</span><span>{team.school_name}</span></>}
          </div>
        )}

        {/* Year label */}
        {selectedYear !== null && (
          <div className="flex items-center gap-2">
            <Calendar size={13} className="text-slate-600" />
            <p className="text-[12px] text-slate-500">
              {selectedYear === 'all'
                ? `All-time · ${availableYears[availableYears.length - 1]}–${availableYears[0]}`
                : `${selectedYear} season`}
            </p>
          </div>
        )}

        {/* Stat badges */}
        {isLoading ? (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-14 bg-app-card border border-app-border rounded-lg animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
            <StatBadge label="Matches"   value={stats.total}                                    icon={<Calendar size={14} />} />
            <StatBadge label="W / L"     value={`${stats.wins} / ${stats.losses}`}              icon={<Trophy size={14} />} />
            <StatBadge label="Win rate"  value={stats.total > 0 ? `${stats.winRate}%` : '—'}   icon={<Target size={14} />} highlight={stats.winRate >= 50} />
            <StatBadge label="Avg score" value={stats.total > 0 ? stats.avgScore : '—'}        icon={<TrendingUp size={14} />} />
            <StatBadge label="High score" value={stats.highScore > 0 ? stats.highScore : '—'}  icon={<Star size={14} />} />
            <StatBadge label="Seasons"   value={availableYears.length}                         icon={<Swords size={14} />} />
          </div>
        )}

        {/* Year-over-year breakdown (all years view only) */}
        {selectedYear === 'all' && yearBreakdown.length > 1 && (
          <div className="bg-app-card border border-app-border rounded-lg overflow-hidden">
            <div className="px-4 py-3 border-b border-app-border">
              <p className="text-[12px] font-medium text-white">Year-over-year summary</p>
            </div>
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-app-border bg-app-muted/20">
                  <th className="text-left px-4 py-2.5 font-medium text-slate-400">Season</th>
                  <th className="text-center px-4 py-2.5 font-medium text-slate-400">Matches</th>
                  <th className="text-center px-4 py-2.5 font-medium text-slate-400">W/L</th>
                  <th className="text-center px-4 py-2.5 font-medium text-slate-400">Win %</th>
                  <th className="text-center px-4 py-2.5 font-medium text-slate-400">Avg score</th>
                  <th className="text-right px-4 py-2.5 font-medium text-slate-400"></th>
                </tr>
              </thead>
              <tbody>
                {yearBreakdown.map((row, idx) => (
                  <tr key={row.year} className={clsx(
                    'border-b border-app-border last:border-0 transition-colors hover:bg-app-muted/20',
                    idx % 2 === 0 ? '' : 'bg-app-muted/10'
                  )}>
                    <td className="px-4 py-2.5 font-medium text-white">{row.year}</td>
                    <td className="px-4 py-2.5 text-center text-slate-400">{row.matches}</td>
                    <td className="px-4 py-2.5 text-center text-slate-400">{row.wins}/{row.matches - row.wins}</td>
                    <td className="px-4 py-2.5 text-center">
                      <span className={clsx('font-medium', row.winRate >= 50 ? 'text-green-400' : 'text-red-400')}>
                        {row.winRate}%
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-center text-slate-300">{row.avgScore}</td>
                    <td className="px-4 py-2.5 text-right">
                      <button
                        onClick={() => setSelectedYear(row.year)}
                        className="text-[11px] text-brand hover:underline"
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Charts */}
        {!isLoading && chartData.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* Alliance score per match */}
            <div className="bg-app-card border border-app-border rounded-lg p-5">
              <p className="text-[12px] font-medium text-white mb-4">Alliance score per match</p>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={chartData} barSize={18}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                  <XAxis dataKey="match" stroke="#475569" fontSize={11} tickLine={false} />
                  <YAxis stroke="#475569" fontSize={11} tickLine={false} axisLine={false} />
                  <Tooltip {...TOOLTIP_STYLE} formatter={(v) => [v ?? 0, 'Score']} />
                  <ReferenceLine y={avgLine} stroke="#f59e0b" strokeDasharray="4 2" strokeWidth={1.5} label={{ value: `avg ${avgLine}`, fill: '#f59e0b', fontSize: 10, position: 'right' }} />
                  <Bar
                    dataKey="allianceScore"
                    radius={[4, 4, 0, 0]}
                    fill="#3b82f6"
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Score trend */}
            <div className="bg-app-card border border-app-border rounded-lg p-5">
              <p className="text-[12px] font-medium text-white mb-4">Score trend</p>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                  <XAxis dataKey="match" stroke="#475569" fontSize={11} tickLine={false} />
                  <YAxis stroke="#475569" fontSize={11} tickLine={false} axisLine={false} />
                  <Tooltip {...TOOLTIP_STYLE} formatter={(v) => [v ?? 0, 'Score']} />
                  <ReferenceLine y={avgLine} stroke="#f59e0b" strokeDasharray="4 2" strokeWidth={1.5} />
                  <Line
                    type="monotone"
                    dataKey="allianceScore"
                    stroke="#10b981"
                    dot={{ fill: '#10b981', r: 3 }}
                    strokeWidth={2}
                    activeDot={{ r: 5 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Robot contribution breakdown (only if data exists) */}
            {chartData.some(d => d.robotContrib > 0) && (
              <div className="bg-app-card border border-app-border rounded-lg p-5 lg:col-span-2">
                <p className="text-[12px] font-medium text-white mb-1">Robot contribution breakdown</p>
                <p className="text-[10px] text-slate-600 mb-4">Auto · Teleop · Endgame per match</p>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={chartData} barSize={14}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                    <XAxis dataKey="match" stroke="#475569" fontSize={11} tickLine={false} />
                    <YAxis stroke="#475569" fontSize={11} tickLine={false} axisLine={false} />
                    <Tooltip {...TOOLTIP_STYLE} />
                    <Bar dataKey="auto"    stackId="a" fill="#8b5cf6" radius={[0,0,0,0]} name="Auto" />
                    <Bar dataKey="teleop"  stackId="a" fill="#3b82f6"                   name="Teleop" />
                    <Bar dataKey="endgame" stackId="a" fill="#10b981" radius={[4,4,0,0]} name="Endgame" />
                  </BarChart>
                </ResponsiveContainer>
                <div className="flex gap-4 mt-2 justify-center">
                  {[['#8b5cf6','Auto'],['#3b82f6','Teleop'],['#10b981','Endgame']].map(([c,l]) => (
                    <div key={l} className="flex items-center gap-1.5 text-[11px] text-slate-500">
                      <div className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ background: c }} />
                      {l}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Match history table */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <p className="text-[13px] font-medium text-white">
              Match history
              {filteredMatches.length > 0 && (
                <span className="text-slate-600 font-normal ml-1.5">
                  · {filteredMatches.length} matches
                </span>
              )}
            </p>
          </div>

          {isLoading ? (
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-10 bg-app-card rounded animate-pulse" />
              ))}
            </div>
          ) : filteredMatches.length === 0 ? (
            <div className="bg-app-card border border-app-border rounded-lg p-8 text-center">
              <Swords size={20} className="text-slate-700 mx-auto mb-2" />
              <p className="text-slate-500 text-sm">
                {selectedYear === 'all' || !selectedYear
                  ? 'No matches found'
                  : `No matches in ${selectedYear}`}
              </p>
              {selectedYear !== 'all' && availableYears.length > 1 && (
                <button
                  onClick={() => setSelectedYear('all')}
                  className="mt-2 text-[11px] text-brand hover:underline"
                >
                  View all years
                </button>
              )}
            </div>
          ) : (
            <div className="border border-app-border rounded-lg overflow-hidden">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-app-border bg-app-card/50">
                    <th className="text-left py-2.5 px-4 font-medium text-slate-500 w-10">W/L</th>
                    <th className="text-left py-2.5 px-4 font-medium text-slate-500">#</th>
                    <th className="text-left py-2.5 px-4 font-medium text-slate-500">Type</th>
                    <th className="text-center py-2.5 px-4 font-medium text-red-400">Red</th>
                    <th className="text-center py-2.5 px-4 font-medium text-blue-400">Blue</th>
                    <th className="text-right py-2.5 px-4 font-medium text-slate-500"></th>
                  </tr>
                </thead>
                <tbody>
                  {filteredMatches.map(match => (
                    <MatchRow key={match.match_id} match={match} teamId={teamIdNum!} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}