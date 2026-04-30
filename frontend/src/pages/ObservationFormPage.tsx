import { useState } from 'react';
import { ArrowLeft, Send } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { clsx } from 'clsx';
import api from '@/api/client';
import { useAuth } from '@/context/AuthContext';
import { eventsQuery, eventMatchesQuery, eventTeamsQuery } from '@/api/queries';

export default function ObservationFormPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();

  // Form state stores human-readable numbers; IDs are resolved at submit time
  const [formData, setFormData] = useState({
    eventId: '',      // event DB id (used to load matches + teams)
    matchId: '',      // match DB id — set when scout picks a match
    teamNumber: '',   // the FRC team number the scout types/picks
    notes: '',
    score: '',
    rating: 3,
  });
  const [error, setError] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const eventIdInt = formData.eventId ? parseInt(formData.eventId) : null;

  // Load matches and teams for the selected event
  const { data: events = [] } = useQuery(eventsQuery());
  const { data: matches = [] } = useQuery(eventMatchesQuery(eventIdInt));
  const { data: eventTeams = [] } = useQuery(eventTeamsQuery(eventIdInt));

  const mutation = useMutation({
    mutationFn: async () => {
      if (!user) throw new Error('User not authenticated');
      if (!formData.eventId || !formData.matchId || !formData.teamNumber) {
        throw new Error('Please fill in all required fields');
      }

      // Resolve team_number → team_id
      const teamNumberInt = parseInt(formData.teamNumber);
      const team = eventTeams.find((t: any) => t.team_number === teamNumberInt);
      if (!team) {
        throw new Error(`Team ${formData.teamNumber} not found in this event`);
      }

      const payload = {
        team_id: team.team_id,
        match_id: parseInt(formData.matchId),
        scout_id: user.user_id,
        notes: formData.notes || null,
        rating: formData.rating,
        actions: formData.score ? { score: parseInt(formData.score) } : null,
        submitted_at: new Date().toISOString(),
      };

      const response = await api.post('/scouting_observations/', payload);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scouting-observations'] });
      setSubmitted(true);
      setTimeout(() => navigate('/observations'), 2000);
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || err.message || 'Failed to submit observation');
    },
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    mutation.mutate();
  };

  if (submitted) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center mx-auto mb-4">
            <span className="text-3xl">✓</span>
          </div>
          <p className="text-white font-medium">Observation recorded</p>
          <p className="text-sm text-slate-600 mt-1">Redirecting...</p>
        </div>
      </div>
    );
  }

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
          <p className="text-[15px] font-medium text-white">Record Observation</p>
          <p className="text-[11px] text-slate-600 mt-0.5">Log what you saw on the field</p>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-6">
        <form onSubmit={handleSubmit} className="max-w-2xl mx-auto space-y-5">
          {/* Error message */}
          {error && (
            <div className="p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}

          {/* Event */}
          <div>
            <label className="text-[11px] font-medium text-slate-600 block mb-2">
              Event<span className="text-red-400">*</span>
            </label>
            <select
              value={formData.eventId}
              onChange={e => setFormData({ ...formData, eventId: e.target.value, matchId: '', teamNumber: '' })}
              className="w-full px-3 py-2 bg-app-card border border-app-border rounded-lg text-white text-sm"
              required
            >
              <option value="">Select an event...</option>
              {events.map((evt: any) => (
                <option key={evt.event_id} value={evt.event_id}>
                  {evt.name} ({evt.season_year})
                </option>
              ))}
            </select>
          </div>

          {/* Match — value is match_id, label shows match_number */}
          <div>
            <label className="text-[11px] font-medium text-slate-600 block mb-2">
              Match number<span className="text-red-400">*</span>
            </label>
            <select
              value={formData.matchId}
              onChange={e => setFormData({ ...formData, matchId: e.target.value })}
              className="w-full px-3 py-2 bg-app-card border border-app-border rounded-lg text-white text-sm"
              required
              disabled={!formData.eventId}
            >
              <option value="">Select a match...</option>
              {matches
                .slice()
                .sort((a: any, b: any) => {
                  const typeOrder: Record<string, number> = { qualification: 0, semifinal: 1, final: 2 };
                  const typeA = typeOrder[a.match_type] ?? 99;
                  const typeB = typeOrder[b.match_type] ?? 99;
                  if (typeA !== typeB) return typeA - typeB;
                  // For semis/finals sort by set number then match number within set
                  const parseKey = (key: string) => {
                    const m = key?.match(/(?:sf|f)(\d+)m(\d+)/);
                    return m ? [parseInt(m[1]), parseInt(m[2])] : [0, a.match_number];
                  };
                  const [aSet, aMatch] = parseKey(a.tba_match_key);
                  const [bSet, bMatch] = parseKey(b.tba_match_key);
                  if (aSet !== bSet) return aSet - bSet;
                  if (aMatch !== bMatch) return aMatch - bMatch;
                  return a.match_number - b.match_number;
                })
                .map((m: any) => {
                  // Parse set/match from TBA key e.g. 2025necmp_sf2m1
                  const parsed = m.tba_match_key?.match(/(?:sf|f)(\d+)m(\d+)/);
                  const typeName = m.match_type.charAt(0).toUpperCase() + m.match_type.slice(1);
                  // FRC convention: "Semifinal 2 (Match 1)" — set number identifies the bracket matchup
                  const label = parsed
                    ? `${typeName} ${parsed[1]}${parseInt(parsed[2]) > 1 ? ` (Match ${parsed[2]})` : ''}`
                    : `${typeName} ${m.match_number}`;
                  return (
                    <option key={m.match_id} value={m.match_id}>
                      {label}
                    </option>
                  );
                })}
            </select>
          </div>

          {/* Team — picks from event roster by team_number */}
          <div>
            <label className="text-[11px] font-medium text-slate-600 block mb-2">
              Team number<span className="text-red-400">*</span>
            </label>
            {eventTeams.length > 0 ? (
              <select
                value={formData.teamNumber}
                onChange={e => setFormData({ ...formData, teamNumber: e.target.value })}
                className="w-full px-3 py-2 bg-app-card border border-app-border rounded-lg text-white text-sm"
                required
                disabled={!formData.eventId}
              >
                <option value="">Select a team...</option>
                {eventTeams
                  .slice()
                  .sort((a: any, b: any) => a.team_number - b.team_number)
                  .map((t: any) => (
                    <option key={t.team_id} value={t.team_number}>
                      {t.team_number}{t.team_name ? ` — ${t.team_name}` : ''}
                    </option>
                  ))}
              </select>
            ) : (
              <input
                type="number"
                value={formData.teamNumber}
                onChange={e => setFormData({ ...formData, teamNumber: e.target.value })}
                placeholder="e.g. 1234"
                className="w-full px-3 py-2 bg-app-card border border-app-border rounded-lg text-white text-sm placeholder:text-slate-600"
                required
              />
            )}
            {formData.teamNumber && eventTeams.length > 0 &&
              !eventTeams.find((t: any) => t.team_number === parseInt(formData.teamNumber)) && (
              <p className="text-red-400 text-xs mt-1">Team {formData.teamNumber} is not registered for this event</p>
            )}
          </div>

          {/* Score */}
          <div>
            <label className="text-[11px] font-medium text-slate-600 block mb-2">
              Match score
            </label>
            <input
              type="number"
              value={formData.score}
              onChange={e => setFormData({ ...formData, score: e.target.value })}
              placeholder="e.g. 125"
              className="w-full px-3 py-2 bg-app-card border border-app-border rounded-lg text-white text-sm placeholder:text-slate-600"
            />
          </div>

          {/* Performance rating */}
          <div>
            <label className="text-[11px] font-medium text-slate-600 block mb-3">
              Performance rating: <span className="text-brand">{formData.rating}/5</span>
            </label>
            <div className="flex items-center gap-2">
              {[1, 2, 3, 4, 5].map(i => (
                <button
                  key={i}
                  type="button"
                  onClick={() => setFormData({ ...formData, rating: i })}
                  className={clsx(
                    'flex-1 py-2 rounded-lg text-sm font-medium transition-colors',
                    formData.rating >= i
                      ? 'bg-brand text-white'
                      : 'bg-app-muted text-slate-600 hover:text-slate-400'
                  )}
                >
                  {i}
                </button>
              ))}
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="text-[11px] font-medium text-slate-600 block mb-2">
              Notes & observations
            </label>
            <textarea
              value={formData.notes}
              onChange={e => setFormData({ ...formData, notes: e.target.value })}
              placeholder="What did you observe? Any notable plays or issues?"
              rows={5}
              className="w-full px-3 py-2 bg-app-card border border-app-border rounded-lg text-white text-sm placeholder:text-slate-600 resize-none"
            />
          </div>

          {/* Submit */}
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="flex-1 px-4 py-2 border border-app-border rounded-lg text-white text-sm font-medium hover:bg-app-card transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="flex-1 px-4 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand/85 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              <Send size={14} />
              {mutation.isPending ? 'Submitting...' : 'Submit'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}