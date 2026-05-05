/**
 * MobileScoutingForm.tsx
 * ======================
 * Phase 2 Tier 10 — Touch-optimised scouting data entry form.
 *
 * Design principles
 * -----------------
 * - Large tap targets (min 44px) throughout
 * - Stepper inputs instead of text fields for numbers
 * - Phase-based layout (Auto → Teleop → Endgame → Review)
 * - Rating via large star/button row
 * - Inline offline indicator
 * - No dropdowns for critical fields — use scrollable button rows
 */

import { useState, type FormEvent } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  Wifi,
  WifiOff,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Star,
  Minus,
  Plus,
} from 'lucide-react';
import { clsx } from 'clsx';
import { useNetworkStatus } from '@/hooks/useNetworkStatus';
import type { ObservationPayload } from '@/services/offlineQueue';
import type { Event, Team } from '@/types/models';

// ── Types ─────────────────────────────────────────────────────────────────────

export interface MobileScoutingFormProps {
  events:    Event[];
  teams:     Team[];
  onSubmit:  (payload: ObservationPayload) => Promise<{ id: number; queued: boolean }>;
  onSuccess: (queued: boolean) => void;
}

type Phase = 'setup' | 'auto' | 'teleop' | 'endgame' | 'review';

const PHASES: Phase[] = ['setup', 'auto', 'teleop', 'endgame', 'review'];
const PHASE_LABELS: Record<Phase, string> = {
  setup:   'Setup',
  auto:    'Autonomous',
  teleop:  'Teleop',
  endgame: 'Endgame',
  review:  'Review & Submit',
};

interface FormState {
  eventId:       number | null;
  teamNumber:    string;
  matchNumber:   string;
  // Scores per phase
  autoScore:     number;
  teleopScore:   number;
  endgameScore:  number;
  // Notes per phase
  autoNotes:     string;
  teleopNotes:   string;
  endgameNotes:  string;
  generalNotes:  string;
  // Rating
  rating:        number;
}

const DEFAULT_STATE: FormState = {
  eventId:      null,
  teamNumber:   '',
  matchNumber:  '',
  autoScore:    0,
  teleopScore:  0,
  endgameScore: 0,
  autoNotes:    '',
  teleopNotes:  '',
  endgameNotes: '',
  generalNotes: '',
  rating:       3,
};

// ── Sub-components ────────────────────────────────────────────────────────────

function PhaseBar({ current }: { current: Phase }) {
  const idx = PHASES.indexOf(current);
  return (
    <div className="flex items-center gap-1 px-4 py-3 bg-app-card border-b border-app-border">
      {PHASES.map((phase, i) => (
        <div key={phase} className="flex items-center gap-1 flex-1 min-w-0">
          <div className={clsx(
            'h-1.5 w-full rounded-full transition-colors',
            i < idx  ? 'bg-brand'
            : i === idx ? 'bg-brand/60'
            : 'bg-app-muted'
          )} />
        </div>
      ))}
    </div>
  );
}

function Stepper({
  label,
  value,
  onChange,
  min = 0,
  max = 999,
  step = 1,
}: {
  label:    string;
  value:    number;
  onChange: (v: number) => void;
  min?:     number;
  max?:     number;
  step?:    number;
}) {
  return (
    <div className="flex items-center justify-between py-4 border-b border-app-border last:border-0">
      <span className="text-sm font-medium text-slate-300">{label}</span>
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => onChange(Math.max(min, value - step))}
          className="w-10 h-10 rounded-xl bg-app-muted text-white flex items-center justify-center active:scale-95 transition-transform"
          aria-label={`Decrease ${label}`}
        >
          <Minus size={16} />
        </button>
        <span className="w-10 text-center text-lg font-mono font-medium text-white tabular-nums">
          {value}
        </span>
        <button
          type="button"
          onClick={() => onChange(Math.min(max, value + step))}
          className="w-10 h-10 rounded-xl bg-brand text-white flex items-center justify-center active:scale-95 transition-transform"
          aria-label={`Increase ${label}`}
        >
          <Plus size={16} />
        </button>
      </div>
    </div>
  );
}

function NoteField({
  label,
  value,
  onChange,
  placeholder,
}: {
  label:       string;
  value:       string;
  onChange:    (v: string) => void;
  placeholder: string;
}) {
  return (
    <div className="mt-4">
      <label className="block text-xs font-medium text-slate-500 mb-2 uppercase tracking-wider">
        {label}
      </label>
      <textarea
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        rows={3}
        className="w-full px-3 py-3 bg-app-card border border-app-border rounded-xl text-white text-sm placeholder:text-slate-600 resize-none focus:outline-none focus:border-brand/50"
      />
    </div>
  );
}

function StarRating({
  value,
  onChange,
}: {
  value:    number;
  onChange: (v: number) => void;
}) {
  return (
    <div className="flex gap-2 justify-center py-4">
      {[1, 2, 3, 4, 5].map(i => (
        <button
          key={i}
          type="button"
          onClick={() => onChange(i)}
          className="p-1 active:scale-90 transition-transform"
          aria-label={`Rating ${i}`}
        >
          <Star
            size={36}
            className={clsx(
              'transition-colors',
              i <= value ? 'fill-brand text-brand' : 'text-app-muted'
            )}
          />
        </button>
      ))}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function MobileScoutingForm({
  events,
  teams,
  onSubmit,
  onSuccess,
}: MobileScoutingFormProps) {
  const { isOnline } = useNetworkStatus();

  const [phase,        setPhase]       = useState<Phase>('setup');
  const [form,         setForm]        = useState<FormState>(DEFAULT_STATE);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError,  setSubmitError]  = useState<string | null>(null);

  // ── Filtered teams for the selected event ──────────────────────────────────
  const eventTeams = form.eventId
    ? teams.filter(t => {
        // Teams don't carry event_id directly — show all and let scouts pick
        return true;
      })
    : teams;

  const selectedTeam = teams.find(
    t => t.team_number === parseInt(form.teamNumber || '0')
  ) ?? null;

  // ── Navigation ─────────────────────────────────────────────────────────────

  const phaseIdx  = PHASES.indexOf(phase);
  const canGoNext = phase === 'setup'
    ? !!form.teamNumber
    : true;

  const goNext = () => {
    if (phaseIdx < PHASES.length - 1) setPhase(PHASES[phaseIdx + 1]);
  };

  const goBack = () => {
    if (phaseIdx > 0) setPhase(PHASES[phaseIdx - 1]);
  };

  // ── Submit ─────────────────────────────────────────────────────────────────

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (isSubmitting) return;

    setIsSubmitting(true);
    setSubmitError(null);

    const payload: ObservationPayload = {
      match_id:      null,
      team_id:       selectedTeam?.team_id ?? null,
      team_number:   parseInt(form.teamNumber),
      event_id:      form.eventId,
      score:         form.autoScore + form.teleopScore + form.endgameScore || null,
      rating:        form.rating,
      notes:         form.generalNotes,
      auto_notes:    form.autoNotes,
      teleop_notes:  form.teleopNotes,
      endgame_notes: form.endgameNotes,
      is_offline:    !isOnline,
    };

    try {
      const result = await onSubmit(payload);
      onSuccess(result.queued);
      // Reset form
      setForm(DEFAULT_STATE);
      setPhase('setup');
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Submission failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  // ── Render phases ──────────────────────────────────────────────────────────

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm(f => ({ ...f, [key]: value }));

  return (
    <form onSubmit={handleSubmit} className="flex flex-col h-full">

      {/* Offline banner */}
      <div className={clsx(
        'flex items-center gap-2 px-4 py-2 text-xs font-medium transition-colors',
        isOnline
          ? 'bg-green-500/10 text-green-400'
          : 'bg-amber-500/10 text-amber-400'
      )}>
        {isOnline
          ? <><Wifi size={12} /> Online — submissions go directly to server</>
          : <><WifiOff size={12} /> Offline — observations saved locally and synced when reconnected</>
        }
      </div>

      {/* Phase progress bar */}
      <PhaseBar current={phase} />

      {/* Phase heading */}
      <div className="px-4 pt-4 pb-2">
        <p className="text-xs text-slate-500 uppercase tracking-wider font-medium">
          Step {phaseIdx + 1} of {PHASES.length}
        </p>
        <h2 className="text-lg font-semibold text-white mt-0.5">
          {PHASE_LABELS[phase]}
        </h2>
      </div>

      {/* Scrollable content area */}
      <div className="flex-1 overflow-y-auto px-4 pb-4">

        {/* ── SETUP ─────────────────────────────────────────────────────── */}
        {phase === 'setup' && (
          <div className="space-y-4 pt-2">

            {/* Event selector */}
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-2 uppercase tracking-wider">
                Event
              </label>
              <div className="flex flex-wrap gap-2">
                {events.slice(0, 12).map(ev => (
                  <button
                    key={ev.event_id}
                    type="button"
                    onClick={() => set('eventId', ev.event_id)}
                    className={clsx(
                      'px-3 py-2 rounded-xl text-sm transition-colors border',
                      form.eventId === ev.event_id
                        ? 'bg-brand border-brand text-white'
                        : 'bg-app-card border-app-border text-slate-400 active:bg-app-muted'
                    )}
                  >
                    {ev.tba_event_key}
                  </button>
                ))}
                {events.length === 0 && (
                  <p className="text-slate-600 text-sm">No events loaded — scouting offline</p>
                )}
              </div>
            </div>

            {/* Team number */}
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-2 uppercase tracking-wider">
                Team Number <span className="text-red-400">*</span>
              </label>
              <input
                type="number"
                inputMode="numeric"
                pattern="[0-9]*"
                value={form.teamNumber}
                onChange={e => set('teamNumber', e.target.value)}
                placeholder="e.g. 1234"
                className="w-full px-4 py-3.5 bg-app-card border border-app-border rounded-xl text-white text-base placeholder:text-slate-600 focus:outline-none focus:border-brand/50"
                required
              />
              {selectedTeam && (
                <p className="mt-1.5 text-xs text-brand">
                  {selectedTeam.team_name ?? `Team ${selectedTeam.team_number}`}
                </p>
              )}
            </div>

            {/* Match number */}
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-2 uppercase tracking-wider">
                Match Number
              </label>
              <input
                type="number"
                inputMode="numeric"
                pattern="[0-9]*"
                value={form.matchNumber}
                onChange={e => set('matchNumber', e.target.value)}
                placeholder="e.g. 12"
                className="w-full px-4 py-3.5 bg-app-card border border-app-border rounded-xl text-white text-base placeholder:text-slate-600 focus:outline-none focus:border-brand/50"
              />
            </div>
          </div>
        )}

        {/* ── AUTO ──────────────────────────────────────────────────────── */}
        {phase === 'auto' && (
          <div className="pt-2">
            <p className="text-xs text-slate-500 mb-4">
              Record autonomous period performance (0:00 – 0:15)
            </p>
            <div className="bg-app-card border border-app-border rounded-xl px-4">
              <Stepper
                label="Auto Score"
                value={form.autoScore}
                onChange={v => set('autoScore', v)}
                max={50}
              />
            </div>
            <NoteField
              label="Auto notes"
              value={form.autoNotes}
              onChange={v => set('autoNotes', v)}
              placeholder="Starting position, game piece actions, mobility…"
            />
          </div>
        )}

        {/* ── TELEOP ────────────────────────────────────────────────────── */}
        {phase === 'teleop' && (
          <div className="pt-2">
            <p className="text-xs text-slate-500 mb-4">
              Record teleoperated period performance (0:15 – 2:15)
            </p>
            <div className="bg-app-card border border-app-border rounded-xl px-4">
              <Stepper
                label="Teleop Score"
                value={form.teleopScore}
                onChange={v => set('teleopScore', v)}
                max={150}
              />
            </div>
            <NoteField
              label="Teleop notes"
              value={form.teleopNotes}
              onChange={v => set('teleopNotes', v)}
              placeholder="Cycle speed, game piece handling, defense, fouls…"
            />
          </div>
        )}

        {/* ── ENDGAME ───────────────────────────────────────────────────── */}
        {phase === 'endgame' && (
          <div className="pt-2">
            <p className="text-xs text-slate-500 mb-4">
              Record endgame performance (2:15 – 2:30)
            </p>
            <div className="bg-app-card border border-app-border rounded-xl px-4">
              <Stepper
                label="Endgame Score"
                value={form.endgameScore}
                onChange={v => set('endgameScore', v)}
                max={30}
              />
            </div>
            <NoteField
              label="Endgame notes"
              value={form.endgameNotes}
              onChange={v => set('endgameNotes', v)}
              placeholder="Climb success/failure, park, harmony attempt…"
            />
          </div>
        )}

        {/* ── REVIEW ────────────────────────────────────────────────────── */}
        {phase === 'review' && (
          <div className="pt-2 space-y-4">

            {/* Summary card */}
            <div className="bg-app-card border border-app-border rounded-xl p-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-slate-500">Team</span>
                <span className="text-white font-medium">
                  {form.teamNumber || '—'}
                  {selectedTeam?.team_name ? ` — ${selectedTeam.team_name}` : ''}
                </span>
              </div>
              {form.eventId && (
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Event</span>
                  <span className="text-white">
                    {events.find(e => e.event_id === form.eventId)?.tba_event_key ?? '—'}
                  </span>
                </div>
              )}
              {form.matchNumber && (
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Match</span>
                  <span className="text-white">#{form.matchNumber}</span>
                </div>
              )}
              <div className="pt-2 border-t border-app-border flex justify-between text-sm">
                <span className="text-slate-500">Auto / Teleop / Endgame</span>
                <span className="text-white font-mono">
                  {form.autoScore} / {form.teleopScore} / {form.endgameScore}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-500">Total</span>
                <span className="text-brand font-semibold font-mono">
                  {form.autoScore + form.teleopScore + form.endgameScore}
                </span>
              </div>
            </div>

            {/* Overall rating */}
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1 uppercase tracking-wider text-center">
                Overall Performance Rating
              </label>
              <StarRating value={form.rating} onChange={v => set('rating', v)} />
            </div>

            {/* General notes */}
            <NoteField
              label="Additional notes"
              value={form.generalNotes}
              onChange={v => set('generalNotes', v)}
              placeholder="Anything else worth noting…"
            />

            {/* Error */}
            {submitError && (
              <div className="flex items-center gap-2 p-3 bg-red-900/20 border border-red-800/40 rounded-xl text-red-400 text-sm">
                <AlertCircle size={16} className="flex-shrink-0" />
                {submitError}
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Bottom nav ─────────────────────────────────────────────────────── */}
      <div className="flex gap-3 px-4 py-4 border-t border-app-border bg-app-sidebar">
        {phase !== 'setup' && (
          <button
            type="button"
            onClick={goBack}
            className="flex items-center gap-1.5 px-4 py-3 border border-app-border rounded-xl text-slate-400 text-sm font-medium active:bg-app-card transition-colors"
          >
            <ChevronLeft size={16} />
            Back
          </button>
        )}

        {phase !== 'review' ? (
          <button
            type="button"
            onClick={goNext}
            disabled={!canGoNext}
            className="flex-1 flex items-center justify-center gap-1.5 py-3 bg-brand text-white rounded-xl text-sm font-medium disabled:opacity-40 active:bg-brand/85 transition-colors"
          >
            Next
            <ChevronRight size={16} />
          </button>
        ) : (
          <button
            type="submit"
            disabled={isSubmitting}
            className="flex-1 flex items-center justify-center gap-2 py-3 bg-brand text-white rounded-xl text-sm font-semibold disabled:opacity-50 active:bg-brand/85 transition-colors"
          >
            {isSubmitting ? (
              <><Loader2 size={16} className="animate-spin" /> Submitting…</>
            ) : (
              <><CheckCircle2 size={16} /> {isOnline ? 'Submit' : 'Save Offline'}</>
            )}
          </button>
        )}
      </div>
    </form>
  );
}