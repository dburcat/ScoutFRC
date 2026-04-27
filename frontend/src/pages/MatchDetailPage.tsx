import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Users } from 'lucide-react';
import { type Match } from '@/types/models';
import { clsx } from 'clsx';

export default function MatchDetailPage() {
  const { matchId } = useParams<{ matchId: string }>();
  const navigate = useNavigate();

  // TODO: Fetch match data from API
  // For now, show placeholder
  const match: Match | null = null;

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
            {match ? `Match ${match.match_number}` : 'Match Details'}
          </p>
          <p className="text-[11px] text-slate-600 mt-0.5">Alliance breakdown</p>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-6">
        {!match ? (
          <div className="flex items-center justify-center h-80">
            <div className="text-center">
              <Users size={32} className="text-slate-700 mx-auto mb-3" />
              <p className="text-slate-500 text-sm">Match not found</p>
              <p className="text-slate-700 text-xs mt-1">Tier 6 — coming soon</p>
            </div>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto space-y-6">
            {/* Match Info */}
            <div className="bg-app-card border border-app-border rounded-lg p-5">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-lg font-medium text-white">Match {match.match_number}</h2>
                <span className="text-xs px-2 py-1 rounded bg-slate-700/50 text-slate-400">
                  {match.match_type}
                </span>
              </div>
              {match.played_at && (
                <p className="text-[11px] text-slate-600">
                  Played: {new Date(match.played_at).toLocaleString()}
                </p>
              )}
            </div>

            {/* Alliances */}
            <div className="grid grid-cols-2 gap-4">
              {['red', 'blue'].map(color => {
                const alliance = match.alliances.find(a => a.color === color);
                if (!alliance) return null;
                return (
                  <div
                    key={color}
                    className={clsx('bg-app-card border rounded-lg p-5', {
                      'border-red-500/30': color === 'red',
                      'border-blue-500/30': color === 'blue',
                    })}
                  >
                    <div className="flex items-center justify-between mb-4">
                      <h3 className={clsx('text-lg font-medium capitalize', {
                        'text-red-400': color === 'red',
                        'text-blue-400': color === 'blue',
                      })}>
                        {color} alliance
                      </h3>
                      {alliance.won !== null && (
                        <span className={clsx('text-xs font-medium px-2 py-1 rounded', {
                          'bg-green-900/30 text-green-400': alliance.won,
                          'bg-red-900/30 text-red-400': !alliance.won,
                        })}>
                          {alliance.won ? 'WON' : 'LOST'}
                        </span>
                      )}
                    </div>

                    <div className="space-y-3">
                      <div className="text-center py-3 bg-app-muted rounded-lg">
                        <p className="text-[11px] text-slate-600 mb-1">Score</p>
                        <p className="text-2xl font-bold text-white">{alliance.total_score ?? '—'}</p>
                      </div>

                      <div>
                        <p className="text-[11px] text-slate-600 mb-2">Teams</p>
                        <div className="space-y-1">
                          {alliance.teams.map((team, i) => (
                            <button
                              key={i}
                              onClick={() => {
                                // Navigate to team profile
                                // TODO: Implement navigation
                              }}
                              className="w-full text-left px-3 py-2 rounded bg-app-muted hover:bg-app-muted/80 transition-colors text-sm text-white font-mono"
                            >
                              Team {team.team_number}
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
