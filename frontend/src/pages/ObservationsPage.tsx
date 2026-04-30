import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ClipboardPen, Plus, Star, Search, AlertCircle, Loader, Trash2 } from 'lucide-react';
import { clsx } from 'clsx';
import { scoutingObservationsQuery } from '@/api/queries';
import { useAuth } from '@/context/AuthContext';
import api from '@/api/client';

interface Observation {
  observation_id: number;
  team_id: number;
  match_id: number;
  scout_id: number;
  notes: string | null;
  rating: number | null;
  actions: Record<string, any> | null;
  submitted_at: string;
  match_number: number | null;
  match_set: number | null;
  match_type: string | null;
  team_number: number | null;
  event_name: string | null;
  event_key: string | null;
}

function StarRating({ rating }: { rating: number | null }) {
  if (rating === null) return <span className="text-slate-600 text-xs">—</span>;
  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map(i => (
        <Star
          key={i}
          size={11}
          className={i <= rating ? 'text-amber-400 fill-amber-400' : 'text-slate-700'}
        />
      ))}
    </div>
  );
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
  });
}

export default function ObservationsPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [search, setSearch] = useState('');
  const [expandedNote, setExpandedNote] = useState<{ team: string; note: string } | null>(null);

  const queryClient = useQueryClient();
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const deleteMutation = useMutation({
    mutationFn: (observationId: number) =>
      api.delete(`/scouting_observations/${observationId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scouting-observations'] });
      setDeletingId(null);
    },
    onError: () => setDeletingId(null),
  });

  const handleDelete = (observationId: number) => {
    if (deletingId === observationId) {
      // Second click — confirmed, do the delete
      deleteMutation.mutate(observationId);
    } else {
      // First click — ask for confirmation
      setDeletingId(observationId);
    }
  };

  const { data: observations = [], isLoading, error, isFetching } = useQuery({
    ...scoutingObservationsQuery(),
    // Cast because the query returns `any` from the API
  });

  const obs = observations as Observation[];

  const filtered = obs.filter(o => {
    const q = search.toLowerCase();
    if (!q) return true;
    return (
      String(o.team_id).includes(q) ||
      String(o.match_id).includes(q) ||
      o.notes?.toLowerCase().includes(q)
    );
  });

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Header */}
      <div className="px-6 py-3.5 border-b border-app-border flex-shrink-0 flex items-center justify-between">
        <div>
          <p className="text-[15px] font-medium text-white">Observations</p>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-[11px] text-slate-600">
              {filtered.length} of {obs.length} records
            </span>
            <div className={clsx('w-1.5 h-1.5 rounded-full flex-shrink-0', {
              'bg-green-500': !isFetching,
              'bg-brand animate-pulse': isFetching,
            })} />
          </div>
        </div>
        <div className="flex items-center gap-2">
          {user ? (
            <button
              onClick={() => navigate('/observations/new')}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-brand text-white text-xs font-medium rounded-lg hover:bg-brand/85 transition-colors"
            >
              <Plus size={13} />
              New
            </button>
          ) : (
            <span className="text-[11px] text-slate-600 bg-app-card border border-app-border px-2 py-1 rounded-lg">
              Sign in to scout
            </span>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto space-y-4">
          {/* Search */}
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-600" />
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search by team, match, or notes…"
              className="w-full pl-9 pr-4 py-2 bg-app-card border border-app-border rounded-lg text-white placeholder:text-slate-600 text-sm outline-none focus:border-brand/60"
            />
          </div>

          {/* States */}
          {isLoading ? (
            <div className="flex items-center justify-center py-16">
              <div className="text-center">
                <Loader size={28} className="text-slate-600 mx-auto mb-3 animate-spin" />
                <p className="text-slate-500 text-sm">Loading observations…</p>
              </div>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center py-16">
              <div className="text-center">
                <AlertCircle size={28} className="text-red-500/50 mx-auto mb-3" />
                <p className="text-slate-500 text-sm">Failed to load observations</p>
                {!user && (
                  <p className="text-slate-700 text-xs mt-1">
                    <Link to="/login" className="text-brand hover:underline">Sign in</Link> to view observations
                  </p>
                )}
              </div>
            </div>
          ) : obs.length === 0 ? (
            <div className="bg-app-card border border-app-border rounded-xl p-12 text-center">
              <ClipboardPen size={32} className="text-slate-700 mx-auto mb-3" />
              <p className="text-slate-500 text-sm">No observations yet</p>
              {user ? (
                <button
                  onClick={() => navigate('/observations/new')}
                  className="mt-4 flex items-center gap-1.5 mx-auto px-4 py-2 bg-brand text-white text-xs font-medium rounded-lg hover:bg-brand/85 transition-colors"
                >
                  <Plus size={13} />
                  Record your first observation
                </button>
              ) : (
                <p className="text-slate-700 text-xs mt-2">
                  <Link to="/login" className="text-brand hover:underline">Sign in</Link> to start scouting
                </p>
              )}
            </div>
          ) : filtered.length === 0 ? (
            <div className="bg-app-card border border-app-border rounded-xl p-8 text-center">
              <p className="text-slate-500 text-sm">No matches for your search</p>
            </div>
          ) : (
            <div className="bg-app-card border border-app-border rounded-lg overflow-hidden">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-app-border bg-app-muted/30">
                    <th className="px-4 py-3 text-left font-medium text-slate-400">Team</th>
                    <th className="px-4 py-3 text-left font-medium text-slate-400 hidden sm:table-cell">Event / Match</th>
                    <th className="px-4 py-3 text-left font-medium text-slate-400">Rating</th>
                    <th className="px-4 py-3 text-left font-medium text-slate-400 hidden md:table-cell">Notes</th>
                    <th className="px-4 py-3 text-right font-medium text-slate-400 hidden lg:table-cell">Logged</th>
                    <th className="px-4 py-3 w-10"></th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((obs, idx) => (
                    <tr
                      key={obs.observation_id}
                      className={clsx(
                        'border-b border-app-border transition-colors',
                        idx % 2 === 0 ? 'bg-app-card' : 'bg-app-muted/10'
                      )}
                    >
                      <td className="px-4 py-3">
                        <Link
                          to={`/teams/${obs.team_id}`}
                          className="font-mono font-medium text-white hover:text-brand transition-colors"
                        >
                          Team {obs.team_number ?? obs.team_id}
                        </Link>
                      </td>
                      <td className="px-4 py-3 hidden sm:table-cell">
                        <div className="flex flex-col gap-0.5">
                          {obs.event_name && (
                            <span className="text-slate-300 text-xs truncate max-w-[180px]">{obs.event_name}</span>
                          )}
                          <span className="text-slate-500 text-xs">
                            {(() => {
                              const type = obs.match_type ? obs.match_type.charAt(0).toUpperCase() + obs.match_type.slice(1) : 'Match';
                              if (obs.match_set != null) {
                                return `${type} — Set ${obs.match_set}, Match ${obs.match_number ?? '?'}`;
                              }
                              return `${type} ${obs.match_number ?? obs.match_id}`;
                            })()}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <StarRating rating={obs.rating} />
                      </td>
                      <td className="px-4 py-3 text-slate-400 max-w-xs hidden md:table-cell">
                        {obs.notes ? (
                          <div className="flex items-center gap-1.5 max-w-[200px]">
                            <span className="truncate text-slate-400">{obs.notes}</span>
                            {obs.notes.length > 40 && (
                              <button
                                onClick={() => setExpandedNote({ team: String(obs.team_number ?? obs.team_id), note: obs.notes! })}
                                className="flex-shrink-0 text-[10px] text-brand hover:text-brand/70 underline transition-colors"
                              >
                                more
                              </button>
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-700">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right text-slate-600 hidden lg:table-cell">
                        {fmtDate(obs.submitted_at)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {deletingId === obs.observation_id ? (
                          <div className="flex items-center justify-end gap-1.5">
                            <span className="text-red-400 text-[11px] whitespace-nowrap">Delete?</span>
                            <button
                              onClick={() => deleteMutation.mutate(obs.observation_id)}
                              disabled={deleteMutation.isPending}
                              className="px-2 py-0.5 rounded text-[11px] font-medium bg-red-500 hover:bg-red-600 text-white transition-colors disabled:opacity-50"
                            >
                              {deleteMutation.isPending ? '…' : 'Yes'}
                            </button>
                            <button
                              onClick={() => setDeletingId(null)}
                              className="px-2 py-0.5 rounded text-[11px] font-medium bg-app-muted hover:bg-app-border text-slate-300 transition-colors"
                            >
                              No
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => setDeletingId(obs.observation_id)}
                            className="p-1.5 rounded transition-colors text-slate-600 hover:text-red-400 hover:bg-red-500/10"
                          >
                            <Trash2 size={13} />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
      {/* Note expand modal */}
      {expandedNote && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
          onClick={() => setExpandedNote(null)}
        >
          <div
            className="bg-app-card border border-app-border rounded-xl shadow-xl max-w-lg w-full mx-4 p-5"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-3">
              <p className="text-[13px] font-medium text-white">Team {expandedNote.team} — Notes</p>
              <button
                onClick={() => setExpandedNote(null)}
                className="text-slate-500 hover:text-slate-300 text-lg leading-none transition-colors"
              >
                ✕
              </button>
            </div>
            <p className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed">{expandedNote.note}</p>
          </div>
        </div>
      )}
    </div>
  );
}