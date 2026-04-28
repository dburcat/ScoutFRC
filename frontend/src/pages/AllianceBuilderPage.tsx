import { useState, useEffect } from 'react';
import { ArrowLeft, X, Plus, Search } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import { clsx } from 'clsx';
import api from '@/api/client';
import { teamsQuery } from '@/api/queries';
import { type Team, type Match } from '@/types/models';

// ── Team avg score cache ────────────────────────────────────────────────────────
// Fetch the avg score for a team using their match history
function useTeamAvgScore(teamId: number | null) {
  return useQuery({
    queryKey: ['team-avg-score', teamId],
    queryFn: async () => {
      if (!teamId) return null;
      const res = await api.get<Match[]>(`/teams/${teamId}/matches?limit=100000`);
      const matches = res.data;
      if (matches.length === 0) return null;

      const scores = matches.flatMap(m =>
        m.alliances.flatMap(a =>
          a.robot_performances
            .filter(rp => rp.team_id === teamId)
            .map(rp => rp.total_score_contribution)
        )
      ).filter(s => s > 0);

      if (scores.length === 0) {
        // Fall back to alliance avg if no per-robot scores
        const allianceScores = matches.flatMap(m =>
          m.alliances
            .filter(a => a.robot_performances.some(rp => rp.team_id === teamId))
            .map(a => (a.total_score ?? 0) / Math.max(a.robot_performances.length, 1))
        );
        if (allianceScores.length === 0) return null;
        return Math.round(allianceScores.reduce((a, b) => a + b, 0) / allianceScores.length);
      }

      return Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
    },
    enabled: !!teamId,
    staleTime: 60_000,
  });
}

// ── Team search input ────────────────────────────────────────────────────────
function TeamSearchInput({
  color,
  teams,
  onAdd,
  disabled,
}: {
  color: 'red' | 'blue';
  teams: Team[];
  onAdd: (teamNumber: number) => void;
  disabled: boolean;
}) {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);

  const results = query.trim().length >= 1
    ? teams.filter(t =>
        t.team_number.toString().startsWith(query.trim()) ||
        t.team_name?.toLowerCase().includes(query.toLowerCase())
      ).slice(0, 8)
    : [];

  const handleSelect = (teamNum: number) => {
    onAdd(teamNum);
    setQuery('');
    setOpen(false);
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && query.trim()) {
      const exact = parseInt(query.trim());
      if (!isNaN(exact)) handleSelect(exact);
    }
    if (e.key === 'Escape') setOpen(false);
  };

  return (
    <div className="relative">
      <div className={clsx(
        'flex items-center gap-2 px-3 py-2 border rounded-lg bg-app-muted',
        color === 'red' ? 'border-red-500/30 focus-within:border-red-400/60'
          : 'border-blue-500/30 focus-within:border-blue-400/60',
        disabled && 'opacity-50 pointer-events-none'
      )}>
        <Search size={12} className="text-slate-600 flex-shrink-0" />
        <input
          value={query}
          onChange={e => { setQuery(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          onKeyDown={handleKey}
          placeholder="Team # or name…"
          className="bg-transparent text-xs text-white placeholder:text-slate-600 outline-none w-full"
          disabled={disabled}
        />
      </div>
      {open && results.length > 0 && (
        <div className="absolute z-10 top-full left-0 right-0 mt-1 bg-app-card border border-app-border rounded-lg shadow-lg overflow-hidden">
          {results.map(t => (
            <button
              key={t.team_id}
              onMouseDown={() => handleSelect(t.team_number)}
              className="w-full flex items-center gap-2 px-3 py-2 hover:bg-app-muted text-left transition-colors"
            >
              <span className="text-xs font-mono font-medium text-white w-10">{t.team_number}</span>
              <span className="text-xs text-slate-400 truncate">{t.team_name ?? '—'}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Team row with live avg score ───────────────────────────────────────────────
function TeamEntry({
  teamNumber,
  teamId,
  color,
  onRemove,
}: {
  teamNumber: number;
  teamId: number | null;
  color: 'red' | 'blue';
  onRemove: () => void;
}) {
  const { data: avgScore, isLoading } = useTeamAvgScore(teamId);

  return (
    <div className="flex items-center justify-between px-3 py-2 bg-app-muted rounded-lg">
      <div className="flex items-center gap-2">
        <span className="font-mono text-white font-medium text-sm">Team {teamNumber}</span>
        <span className="text-[10px] text-slate-600">
          {isLoading ? '…' : avgScore !== null && avgScore !== undefined ? `~${avgScore} pts/match` : 'no data'}
        </span>
      </div>
      <button
        onClick={onRemove}
        className="text-slate-500 hover:text-red-400 transition-colors p-0.5"
      >
        <X size={14} />
      </button>
    </div>
  );
}

// ── Projected score for an alliance ───────────────────────────────────────────
function useProjectedScore(teamNumbers: number[], allTeams: Team[]) {
  // Get team IDs for the given team numbers
  const teamIds = teamNumbers.map(num =>
    allTeams.find(t => t.team_number === num)?.team_id ?? null
  );

  const q0 = useTeamAvgScore(teamIds[0] ?? null);
  const q1 = useTeamAvgScore(teamIds[1] ?? null);
  const q2 = useTeamAvgScore(teamIds[2] ?? null);
  const scores = [q0.data, q1.data, q2.data]
    .slice(0, teamNumbers.length)
    .filter((s): s is number => s !== null && s !== undefined);

  if (teamNumbers.length === 0) return { score: null, hasData: false };
  if (scores.length === 0) return { score: null, hasData: false };

  // Sum contributions (each robot's avg contribution)
  return { score: scores.reduce((a, b) => a + b, 0), hasData: true };
}

// ── Main Page ──────────────────────────────────────────────────────────────────
export default function AllianceBuilderPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [red, setRed] = useState<number[]>([]);
  const [blue, setBlue] = useState<number[]>([]);
  const [allianceName, setAllianceName] = useState('');
  const [error, setError] = useState('');

  const { data: allTeams = [] } = useQuery(teamsQuery());

  // Helper: get team_id from team_number
  const getTeamId = (num: number) =>
    allTeams.find(t => t.team_number === num)?.team_id ?? null;

  const redProjected  = useProjectedScore(red,  allTeams);
  const blueProjected = useProjectedScore(blue, allTeams);

  const mutation = useMutation({
    mutationFn: async () => {
      const payload = {
        name: allianceName || undefined,
        red_teams: red.join(','),
        blue_teams: blue.join(','),
      };
      const response = await api.post('/user_alliances/', payload);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-alliances'] });
      setTimeout(() => navigate('/'), 2000);
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to save alliance');
    },
  });

  const handleAddTeam = (color: 'red' | 'blue', teamNum: number) => {
    const arr = color === 'red' ? red : blue;
    if (arr.length < 3 && !arr.includes(teamNum)) {
      if (color === 'red') setRed([...arr, teamNum]);
      else setBlue([...arr, teamNum]);
    }
  };

  const handleRemoveTeam = (color: 'red' | 'blue', idx: number) => {
    const arr = color === 'red' ? red : blue;
    if (color === 'red') setRed(arr.filter((_, i) => i !== idx));
    else setBlue(arr.filter((_, i) => i !== idx));
  };

  const handleSave = () => {
    setError('');
    if (red.length === 0 || blue.length === 0) {
      setError('Please select at least one team for each alliance');
      return;
    }
    mutation.mutate();
  };

  if (mutation.isPending) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="text-center">
          <div className="animate-spin w-8 h-8 border-2 border-brand border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-white font-medium">Saving alliance...</p>
        </div>
      </div>
    );
  }

  if (mutation.isSuccess) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center mx-auto mb-4">
            <span className="text-3xl">✓</span>
          </div>
          <p className="text-white font-medium">Alliance saved</p>
          <p className="text-sm text-slate-600 mt-1">Redirecting...</p>
        </div>
      </div>
    );
  }

  const teamsForColor = (color: 'red' | 'blue') => (color === 'red' ? red : blue);
  const projectedForColor = (color: 'red' | 'blue') =>
    color === 'red' ? redProjected : blueProjected;

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
            <p className="text-[15px] font-medium text-white">Alliance Builder</p>
            <p className="text-[11px] text-slate-600 mt-0.5">Plan your strategy</p>
          </div>
        </div>
        <button
          onClick={handleSave}
          disabled={red.length === 0 || blue.length === 0 || mutation.isPending}
          className="px-4 py-1.5 bg-brand text-white text-xs font-medium rounded-lg hover:bg-brand/85 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Save Alliance
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto">
          {error && (
            <div className="mb-4 p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}

          {/* Alliance name */}
          <div className="mb-6">
            <label className="text-[11px] font-medium text-slate-600 block mb-2">
              Alliance name (optional)
            </label>
            <input
              type="text"
              value={allianceName}
              onChange={e => setAllianceName(e.target.value)}
              placeholder="e.g. Red Power Play"
              className="w-full px-3 py-2 bg-app-card border border-app-border rounded-lg text-white placeholder:text-slate-600 text-sm"
            />
          </div>

          {/* Alliance columns */}
          <div className="grid grid-cols-2 gap-5">
            {(['red', 'blue'] as const).map(color => {
              const arr = teamsForColor(color);
              const projected = projectedForColor(color);
              return (
                <div
                  key={color}
                  className={clsx(
                    'bg-app-card border rounded-lg p-5',
                    color === 'red' ? 'border-red-500/20' : 'border-blue-500/20'
                  )}
                >
                  <div className="mb-4">
                    <h3 className={clsx('text-sm font-medium capitalize mb-1', {
                      'text-red-400':  color === 'red',
                      'text-blue-400': color === 'blue',
                    })}>
                      {color} Alliance
                    </h3>
                    <p className="text-xs text-slate-600">{arr.length}/3 teams</p>
                  </div>

                  {/* Selected teams */}
                  <div className="space-y-2 mb-4">
                    {arr.map((teamNum, idx) => (
                      <TeamEntry
                        key={`${color}-${teamNum}`}
                        teamNumber={teamNum}
                        teamId={getTeamId(teamNum)}
                        color={color}
                        onRemove={() => handleRemoveTeam(color, idx)}
                      />
                    ))}
                  </div>

                  {/* Projected score */}
                  <div className="mb-4 p-3 bg-app-muted rounded-lg">
                    <p className="text-[10px] text-slate-600 mb-1">Projected alliance score</p>
                    {arr.length === 0 ? (
                      <p className="text-xl font-bold text-slate-600">—</p>
                    ) : projected.hasData ? (
                      <div>
                        <p className="text-xl font-bold text-white">{projected.score}</p>
                        <p className="text-[10px] text-slate-600 mt-0.5">
                          Sum of per-robot avg contributions
                        </p>
                      </div>
                    ) : (
                      <p className="text-sm text-slate-600">No match data yet</p>
                    )}
                  </div>

                  {/* Add team search */}
                  {arr.length < 3 && (
                    <TeamSearchInput
                      color={color}
                      teams={allTeams.filter(t => ![...red, ...blue].includes(t.team_number))}
                      onAdd={num => handleAddTeam(color, num)}
                      disabled={false}
                    />
                  )}
                </div>
              );
            })}
          </div>

          {/* Comparison row */}
          {(redProjected.hasData || blueProjected.hasData) && (
            <div className="mt-5 p-4 bg-app-card border border-app-border rounded-lg">
              <p className="text-[11px] text-slate-600 mb-3">Projected matchup</p>
              <div className="flex items-center gap-3">
                <span className="text-red-400 font-bold text-lg w-10 text-right">
                  {redProjected.score ?? '—'}
                </span>
                {redProjected.score && blueProjected.score ? (
                  <div className="flex-1 flex rounded-full overflow-hidden h-2.5">
                    {(() => {
                      const total = redProjected.score + blueProjected.score;
                      const rPct  = Math.round((redProjected.score / total) * 100);
                      return (
                        <>
                          <div className="bg-red-500" style={{ width: `${rPct}%` }} />
                          <div className="bg-blue-500" style={{ width: `${100 - rPct}%` }} />
                        </>
                      );
                    })()}
                  </div>
                ) : (
                  <div className="flex-1 h-2.5 bg-app-muted rounded-full" />
                )}
                <span className="text-blue-400 font-bold text-lg w-10">
                  {blueProjected.score ?? '—'}
                </span>
              </div>
            </div>
          )}

          <div className="mt-4 p-4 bg-app-card border border-app-border rounded-lg">
            <p className="text-[11px] text-slate-600">
              💡 <span className="font-medium">Tip:</span> Search by team number or name. Projected scores are calculated from each robot's average per-match score contribution across all recorded matches.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}