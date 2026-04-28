import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Clock, CheckCircle, AlertCircle, Loader } from 'lucide-react';
import { type Match, type Alliance } from '@/types/models';
import { eventTeamsQuery, matchQuery } from '@/api/queries';
import { clsx } from 'clsx';

// ── Helpers ────────────────────────────────────────────────────────────────────
function fmtDate(iso: string) {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: 'numeric', minute: '2-digit',
  });
}

function matchTypeLabel(type: string) {
  return type === 'qualification' ? 'Qualification'
    : type === 'semifinal' ? 'Semifinal'
    : 'Final';
}

// ── Status badge ───────────────────────────────────────────────────────────────
function StatusBadge({ status }: { status: Match['processing_status'] }) {
  return (
    <span className={clsx('flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-1 rounded-full', {
      'bg-slate-700/50 text-slate-400':    status === 'pending',
      'bg-amber-900/30 text-amber-400':    status === 'processing',
      'bg-green-900/30 text-green-400':    status === 'complete',
      'bg-red-900/30 text-red-400':        status === 'failed',
    })}>
      {status === 'complete'    && <CheckCircle size={11} />}
      {status === 'failed'      && <AlertCircle size={11} />}
      {status === 'processing'  && <Loader size={11} className="animate-spin" />}
      {status === 'pending'     && <Clock size={11} />}
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

// ── Alliance panel ─────────────────────────────────────────────────────────────
function AlliancePanel({
  alliance,
  teamNumberById,
}: {
  alliance: Alliance;
  teamNumberById: Map<number, number>;
}) {
  const isRed = alliance.color === 'red';

  return (
    <div className={clsx('bg-app-card border rounded-xl p-5 flex flex-col gap-4', {
      'border-red-500/30':  isRed,
      'border-blue-500/30': !isRed,
    })}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className={clsx('text-base font-semibold capitalize', {
          'text-red-400':  isRed,
          'text-blue-400': !isRed,
        })}>
          {alliance.color} Alliance
        </h3>
        {alliance.won !== null && (
          <span className={clsx('text-xs font-bold px-2.5 py-1 rounded-full', {
            'bg-green-900/30 text-green-400': alliance.won,
            'bg-red-900/20 text-red-500':     !alliance.won,
          })}>
            {alliance.won ? '🏆 WON' : 'LOST'}
          </span>
        )}
      </div>

      {/* Score */}
      <div className="text-center py-4 bg-app-muted rounded-lg">
        <p className="text-[10px] text-slate-600 uppercase tracking-widest mb-1">Final Score</p>
        <p className={clsx('text-4xl font-bold', {
          'text-red-300':   isRed && alliance.won === true,
          'text-blue-300':  !isRed && alliance.won === true,
          'text-slate-500': alliance.won === false,
          'text-white':     alliance.won === null,
        })}>
          {alliance.total_score ?? '—'}
        </p>
        {alliance.rp_earned !== null && (
          <p className="text-[11px] text-slate-600 mt-1">
            {alliance.rp_earned} ranking point{alliance.rp_earned !== 1 ? 's' : ''} earned
          </p>
        )}
      </div>

      {/* Robot performances */}
      {alliance.robot_performances && alliance.robot_performances.length > 0 && (
        <div className="space-y-2">
          <p className="text-[10px] text-slate-600 uppercase tracking-widest">Robots</p>
          {alliance.robot_performances.map((rp) => (
            <Link
              key={rp.perf_id}
              to={`/teams/${rp.team_id}`}
              className="flex items-center justify-between px-3 py-2.5 rounded-lg bg-app-muted hover:bg-app-border transition-colors group"
            >
              <div className="flex items-center gap-2.5">
                <span className={clsx('text-[10px] font-medium px-1.5 py-0.5 rounded', {
                  'bg-red-900/30 text-red-400':   isRed,
                  'bg-blue-900/30 text-blue-400':  !isRed,
                })}>
                  R{rp.alliance_position}
                </span>
                <span className="text-white font-mono font-medium group-hover:text-brand transition-colors">
                  Team {teamNumberById.get(rp.team_id) ?? rp.team_id}
                </span>
              </div>
              <div className="flex items-center gap-3 text-[11px]">
                {(rp.auto_score > 0 || rp.teleop_score > 0 || rp.endgame_score > 0) && (
                  <div className="flex gap-2 text-slate-500">
                    <span title="Auto">A:{rp.auto_score}</span>
                    <span title="Teleop">T:{rp.teleop_score}</span>
                    <span title="Endgame">E:{rp.endgame_score}</span>
                  </div>
                )}
                <span className="text-slate-400 font-medium">
                  {rp.total_score_contribution > 0 ? `${rp.total_score_contribution} pts` : '—'}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Score comparison bar ───────────────────────────────────────────────────────
function ScoreBar({ match }: { match: Match }) {
  const red  = match.alliances.find(a => a.color === 'red');
  const blue = match.alliances.find(a => a.color === 'blue');
  const rs = red?.total_score ?? 0;
  const bs = blue?.total_score ?? 0;
  const total = rs + bs;
  if (total === 0) return null;

  const redPct  = Math.round((rs / total) * 100);
  const bluePct = 100 - redPct;

  return (
    <div className="bg-app-card border border-app-border rounded-xl p-5">
      <p className="text-[11px] text-slate-600 mb-3 text-center">Score comparison</p>
      <div className="flex items-center gap-3">
        <span className="text-red-400 font-bold text-lg w-10 text-right">{rs}</span>
        <div className="flex-1 flex rounded-full overflow-hidden h-3">
          <div className="bg-red-500 transition-all" style={{ width: `${redPct}%` }} />
          <div className="bg-blue-500 transition-all" style={{ width: `${bluePct}%` }} />
        </div>
        <span className="text-blue-400 font-bold text-lg w-10">{bs}</span>
      </div>
      <div className="flex justify-between mt-1.5 text-[10px] text-slate-600">
        <span>Red {redPct}%</span>
        <span>Blue {bluePct}%</span>
      </div>
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────────
export default function MatchDetailPage() {
  const { matchId } = useParams<{ matchId: string }>();
  const navigate = useNavigate();
  const matchIdNum = matchId ? parseInt(matchId) : null;

  const { data: match, isLoading, error } = useQuery(matchQuery(matchIdNum));
  const { data: eventTeams = [] } = useQuery(eventTeamsQuery(match?.event_id ?? null));
  const teamNumberById = new Map(eventTeams.map((t) => [t.team_id, t.team_number]));

  // ── Loading ──
  if (isLoading) {
    return (
      <div className="flex flex-col flex-1 min-h-0">
        <div className="px-6 py-3.5 border-b border-app-border flex items-center gap-3 flex-shrink-0">
          <button onClick={() => navigate(-1)} className="text-slate-500 hover:text-slate-300 p-1">
            <ArrowLeft size={18} />
          </button>
          <div className="h-4 w-40 bg-app-muted rounded animate-pulse" />
        </div>
        <div className="flex-1 p-6 grid grid-cols-1 lg:grid-cols-2 gap-5">
          {[0, 1].map(i => (
            <div key={i} className="bg-app-card border border-app-border rounded-xl p-5 h-64 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  // ── Error / Not found ──
  if (error || !match) {
    return (
      <div className="flex flex-col flex-1 min-h-0">
        <div className="px-6 py-3.5 border-b border-app-border flex items-center gap-3 flex-shrink-0">
          <button onClick={() => navigate(-1)} className="text-slate-500 hover:text-slate-300 p-1">
            <ArrowLeft size={18} />
          </button>
          <p className="text-[15px] font-medium text-white">Match Details</p>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <AlertCircle size={32} className="text-slate-700 mx-auto mb-3" />
            <p className="text-slate-500 text-sm">Match not found</p>
            <p className="text-slate-700 text-xs mt-1">ID #{matchIdNum}</p>
          </div>
        </div>
      </div>
    );
  }

  const red  = match.alliances.find(a => a.color === 'red');
  const blue = match.alliances.find(a => a.color === 'blue');

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
              {matchTypeLabel(match.match_type)} Match {match.match_number}
            </p>
            <p className="text-[11px] text-slate-600 font-mono mt-0.5">
              {match.tba_match_key}
            </p>
          </div>
        </div>
        <StatusBadge status={match.processing_status} />
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-5xl mx-auto space-y-5">

          {/* Meta info row */}
          <div className="flex flex-wrap gap-3">
            {match.played_at && (
              <div className="bg-app-card border border-app-border rounded-lg px-3 py-2 flex items-center gap-2 text-xs text-slate-400">
                <Clock size={13} className="text-slate-600" />
                {fmtDate(match.played_at)}
              </div>
            )}
            <div className="bg-app-card border border-app-border rounded-lg px-3 py-2 text-xs text-slate-400">
              Type: <span className="text-white font-medium">{matchTypeLabel(match.match_type)}</span>
            </div>
            <div className="bg-app-card border border-app-border rounded-lg px-3 py-2 text-xs text-slate-400">
              Match #<span className="text-white font-medium">{match.match_number}</span>
            </div>
            {match.video_url && (
              <a
                href={match.video_url}
                target="_blank"
                rel="noopener noreferrer"
                className="bg-app-card border border-app-border rounded-lg px-3 py-2 text-xs text-brand hover:text-brand/80 transition-colors"
              >
                ▶ Watch video
              </a>
            )}
          </div>

          {/* Score comparison */}
          <ScoreBar match={match} />

          {/* Alliance panels */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {red  && <AlliancePanel alliance={red} teamNumberById={teamNumberById} />}
            {blue && <AlliancePanel alliance={blue} teamNumberById={teamNumberById} />}
          </div>

          {/* TBA link */}
          <div className="p-4 bg-app-card border border-app-border rounded-lg">
            <p className="text-[11px] text-slate-600">
              🔗 View full breakdown on{' '}
              <a
                href={`https://www.thebluealliance.com/match/${match.tba_match_key}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-brand hover:underline"
              >
                The Blue Alliance
              </a>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}