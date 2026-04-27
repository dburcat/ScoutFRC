import { useQuery } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Trophy, TrendingUp } from 'lucide-react';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import { type Event, type Team, type Match } from '@/types/models';
import { eventQuery, eventTeamsQuery, eventMatchesQuery } from '@/api/queries';
import { clsx } from 'clsx';

function RankingRow({ rank, team, avgScore, wins, matches }: {
  rank: number
  team: Team
  avgScore: number
  wins: number
  matches: number
}) {
  return (
    <tr className="hover:bg-app-card/50 transition-colors">
      <td className="py-3 px-4">
        <div className="flex items-center justify-center w-8 h-8 rounded-full bg-app-muted font-medium text-sm">
          {rank}
        </div>
      </td>
      <td className="py-3 px-4">
        <div>
          <p className="text-white font-medium">{team.team_number}</p>
          <p className="text-xs text-slate-600">{team.team_name || '—'}</p>
        </div>
      </td>
      <td className="py-3 px-4 text-center font-mono font-medium text-lg text-white">
        {avgScore.toFixed(1)}
      </td>
      <td className="py-3 px-4 text-center">
        <span className="inline-block px-2 py-1 bg-green-900/20 text-green-400 text-xs font-medium rounded">
          {wins}W
        </span>
      </td>
      <td className="py-3 px-4 text-center text-slate-500">
        {matches}
      </td>
    </tr>
  );
}

export default function EventAnalyticsPage() {
  const { eventId } = useParams<{ eventId: string }>();
  const navigate = useNavigate();
  const eventIdNum = eventId ? parseInt(eventId) : null;

  const { data: event } = useQuery(eventQuery(eventIdNum!));
  const { data: teams = [] } = useQuery(eventTeamsQuery(eventIdNum));
  const { data: matches = [] } = useQuery(eventMatchesQuery(eventIdNum));

  // Calculate rankings
  const teamStats = teams.map(team => {
    const teamMatches = matches.filter(m =>
      m.alliances.some(a =>
        a.teams.some(t => t.team_id === team.team_id)
      )
    );

    const wins = teamMatches.filter(m => {
      const alliance = m.alliances.find(a =>
        a.teams.some(t => t.team_id === team.team_id) && a.won
      );
      return alliance !== undefined;
    }).length;

    const avgScore = teamMatches.length > 0
      ? Math.round(
          teamMatches.reduce((acc, m) => {
            const alliance = m.alliances.find(a =>
              a.teams.some(t => t.team_id === team.team_id)
            );
            return acc + (alliance?.total_score ?? 0);
          }, 0) / teamMatches.length
        )
      : 0;

    return {
      team,
      avgScore,
      wins,
      matches: teamMatches.length,
    };
  });

  const sorted = [...teamStats].sort((a, b) => b.avgScore - a.avgScore);
  const top10 = sorted.slice(0, 10);

  // Prepare chart data
  const barChartData = top10.map(stat => ({
    name: `${stat.team.team_number}`,
    score: stat.avgScore,
  }));

  const redWins = matches.filter(m =>
    m.alliances.find(a => a.color === 'red' && a.won)
  ).length;
  const blueWins = matches.filter(m =>
    m.alliances.find(a => a.color === 'blue' && a.won)
  ).length;

  const pieChartData = [
    { name: 'Red Wins', value: redWins },
    { name: 'Blue Wins', value: blueWins },
  ];

  const lineChartData = matches
    .sort((a, b) => (a.match_number ?? 0) - (b.match_number ?? 0))
    .map((match, idx) => {
      const redScore = match.alliances.find(a => a.color === 'red')?.total_score ?? 0;
      const blueScore = match.alliances.find(a => a.color === 'blue')?.total_score ?? 0;
      return {
        match: match.match_number || idx + 1,
        red: redScore,
        blue: blueScore,
      };
    });

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Header */}
      <div className="px-6 py-3.5 border-b border-app-border flex-shrink-0 flex items-center gap-3">
        <button
          onClick={() => navigate(-1)}
          className="text-slate-500 hover:text-slate-300 transition-colors p-1"
        >
          <ArrowLeft size={18} />
        </button>
        <div>
          <p className="text-[15px] font-medium text-white">
            {event?.name || 'Event Analytics'}
          </p>
          <p className="text-[11px] text-slate-600 mt-0.5">Team rankings & performance</p>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-6xl mx-auto space-y-6">
          {/* Stats cards */}
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-app-card border border-app-border rounded-lg p-4">
              <p className="text-[10px] text-slate-600 mb-1">Total teams</p>
              <p className="text-2xl font-bold text-white">{teams.length}</p>
            </div>
            <div className="bg-app-card border border-app-border rounded-lg p-4">
              <p className="text-[10px] text-slate-600 mb-1">Total matches</p>
              <p className="text-2xl font-bold text-white">{matches.length}</p>
            </div>
            <div className="bg-app-card border border-app-border rounded-lg p-4">
              <p className="text-[10px] text-slate-600 mb-1">Avg score</p>
              <p className="text-2xl font-bold text-white">
                {matches.length > 0
                  ? Math.round(
                      matches.reduce(
                        (acc, m) =>
                          acc + 
                          m.alliances.reduce((s, a) => s + (a.total_score ?? 0), 0),
                        0
                      ) / (matches.length * 2)
                    )
                  : '—'}
              </p>
            </div>
          </div>

          {/* Charts Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Bar Chart - Top Teams */}
            <div className="bg-app-card border border-app-border rounded-lg p-6">
              <h3 className="text-base font-medium text-white mb-4">Top 10 Teams by Avg Score</h3>
              {barChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={barChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} />
                    <YAxis stroke="#94a3b8" fontSize={12} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1e293b',
                        border: '1px solid #475569',
                        borderRadius: '0.5rem',
                        color: '#fff',
                      }}
                    />
                    <Bar dataKey="score" fill="#3b82f6" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-[300px] flex items-center justify-center text-slate-600">
                  No data available
                </div>
              )}
            </div>

            {/* Pie Chart - Red vs Blue */}
            <div className="bg-app-card border border-app-border rounded-lg p-6">
              <h3 className="text-base font-medium text-white mb-4">Win Distribution</h3>
              {pieChartData.some(d => d.value > 0) ? (
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={pieChartData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, value }) => `${name}: ${value}`}
                      outerRadius={100}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      <Cell fill="#ef4444" />
                      <Cell fill="#3b82f6" />
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1e293b',
                        border: '1px solid #475569',
                        borderRadius: '0.5rem',
                        color: '#fff',
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-[300px] flex items-center justify-center text-slate-600">
                  No data available
                </div>
              )}
            </div>
          </div>

          {/* Line Chart - Match Progression */}
          <div className="bg-app-card border border-app-border rounded-lg p-6">
            <h3 className="text-base font-medium text-white mb-4">Match Scores Over Time</h3>
            {lineChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={lineChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="match" stroke="#94a3b8" fontSize={12} />
                  <YAxis stroke="#94a3b8" fontSize={12} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      border: '1px solid #475569',
                      borderRadius: '0.5rem',
                      color: '#fff',
                    }}
                  />
                  <Legend />
                  <Line type="monotone" dataKey="red" stroke="#ef4444" dot={false} strokeWidth={2} />
                  <Line type="monotone" dataKey="blue" stroke="#3b82f6" dot={false} strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-slate-600">
                No data available
              </div>
            )}
          </div>

          {/* Rankings table */}
          <div className="bg-app-card border border-app-border rounded-lg overflow-hidden">
            <div className="px-6 py-4 border-b border-app-border">
              <h3 className="text-base font-medium text-white flex items-center gap-2">
                <Trophy size={18} className="text-amber-400" />
                Full Rankings
              </h3>
            </div>

            {sorted.length === 0 ? (
              <div className="p-8 text-center text-slate-600">
                <p>No team data available yet</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="bg-app-muted border-b border-app-border">
                      <th className="py-2 px-4 text-left font-medium text-slate-600">#</th>
                      <th className="py-2 px-4 text-left font-medium text-slate-600">Team</th>
                      <th className="py-2 px-4 text-center font-medium text-slate-600">Avg Score</th>
                      <th className="py-2 px-4 text-center font-medium text-slate-600">Wins</th>
                      <th className="py-2 px-4 text-center font-medium text-slate-600">Matches</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sorted.map((stat, idx) => (
                      <RankingRow
                        key={stat.team.team_id}
                        rank={idx + 1}
                        team={stat.team}
                        avgScore={stat.avgScore}
                        wins={stat.wins}
                        matches={stat.matches}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Info */}
          <div className="p-4 bg-app-card border border-app-border rounded-lg">
            <p className="text-[11px] text-slate-600">
              📊 <span className="font-medium">Tier 8:</span> Real-time analytics with bar, pie, and line charts. Advanced metrics (OPR/EPA) coming in Phase 2.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
