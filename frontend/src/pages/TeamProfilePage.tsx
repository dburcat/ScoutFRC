import { useQuery } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Trophy, Users, TrendingUp, Calendar, Target,
} from 'lucide-react';
import { type Team, type Match } from '@/types/models';
import { teamMatchesQuery } from '@/api/queries';
import { clsx } from 'clsx';

function StatBadge({ label, value, icon: Icon }: { label: string; value: string | number; icon: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 bg-app-card border border-app-border rounded-lg px-3 py-2">
      <div className="text-brand flex-shrink-0">{Icon}</div>
      <div>
        <p className="text-[10px] text-slate-600">{label}</p>
        <p className="text-sm font-medium text-white">{value}</p>
      </div>
    </div>
  );
}

function MatchRow({ match }: { match: Match }) {
  const red = match.alliances.find(a => a.color === 'red');
  const blue = match.alliances.find(a => a.color === 'blue');

  return (
    <tr className="hover:bg-app-card/50 transition-colors">
      <td className="py-3 px-4 text-white font-mono text-sm">{match.match_number}</td>
      <td className="py-3 px-4 text-slate-400 text-sm">
        {match.match_type === 'qualification' ? 'Qual'
          : match.match_type === 'semifinal' ? 'SF'
          : 'Final'}
      </td>
      <td className="py-3 px-4">
        <span className={clsx('text-sm font-medium', {
          'text-green-400': red?.won,
          'text-red-400': red?.won === false,
          'text-slate-500': red?.won === null,
        })}>
          {red?.total_score ?? '—'}
        </span>
      </td>
      <td className="py-3 px-4">
        <span className={clsx('text-sm font-medium', {
          'text-green-400': blue?.won,
          'text-blue-400': blue?.won === false,
          'text-slate-500': blue?.won === null,
        })}>
          {blue?.total_score ?? '—'}
        </span>
      </td>
      <td className="py-3 px-4 text-right">
        <span className="text-[11px] px-2 py-1 rounded bg-slate-700/50 text-slate-400">
          {match.processing_status === 'complete' ? '✓' : '◌'}
        </span>
      </td>
    </tr>
  );
}

export default function TeamProfilePage() {
  const { teamId } = useParams<{ teamId: string }>();
  const navigate = useNavigate();
  const teamIdNum = teamId ? parseInt(teamId) : null;

  const { data: matches = [], isLoading } = useQuery(teamMatchesQuery(teamIdNum));

  // Calculate stats from matches
  const total = matches.length;
  const wins = matches.filter(m => {
    const alliance = m.alliances.find(a => a.won);
    return alliance !== undefined;
  }).length;
  const avgScore = total > 0
    ? Math.round(matches.reduce((acc, m) => {
      const alliance = m.alliances.find(a => a.won !== null);
      return acc + (alliance?.total_score ?? 0);
    }, 0) / total)
    : 0;

  if (!teamIdNum) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-slate-500">Team not found</p>
      </div>
    );
  }

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
            <p className="text-[15px] font-medium text-white">Team {teamIdNum}</p>
            <p className="text-[11px] text-slate-600 mt-0.5">Robot performance profile</p>
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-6 space-y-5">
        {/* Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatBadge label="Matches" value={total} icon={<Calendar size={16} />} />
          <StatBadge label="Wins" value={`${wins}/${total}`} icon={<Trophy size={16} />} />
          <StatBadge label="Avg Score" value={avgScore} icon={<TrendingUp size={16} />} />
          <StatBadge label="Win Rate" value={total > 0 ? `${Math.round((wins / total) * 100)}%` : '—'} icon={<Target size={16} />} />
        </div>

        {/* Matches table */}
        <div>
          <h3 className="text-[13px] font-medium text-white mb-3">Match history</h3>
          {isLoading ? (
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-12 bg-app-card rounded animate-pulse" />
              ))}
            </div>
          ) : matches.length === 0 ? (
            <div className="bg-app-card border border-app-border rounded-lg p-8 text-center">
              <Users size={20} className="text-slate-700 mx-auto mb-2" />
              <p className="text-slate-500 text-sm">No matches found</p>
            </div>
          ) : (
            <div className="border border-app-border rounded-lg overflow-hidden">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-app-border bg-app-card/50">
                    <th className="text-left py-2 px-4 font-medium text-slate-600">#</th>
                    <th className="text-left py-2 px-4 font-medium text-slate-600">Type</th>
                    <th className="text-left py-2 px-4 font-medium text-red-400">Red</th>
                    <th className="text-left py-2 px-4 font-medium text-blue-400">Blue</th>
                    <th className="text-right py-2 px-4 font-medium text-slate-600">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-app-border">
                  {matches.map(match => (
                    <MatchRow key={match.match_id} match={match} />
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
