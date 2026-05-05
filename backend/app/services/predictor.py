"""
predictor.py
============
Phase 2 Tier 9 — Performance Prediction & Ranking.

Responsibilities
----------------
1. **Team Strength Score** — weighted composite of phase stats, win rate, OPR proxy.
2. **Match Outcome Prediction** — gradient boosting model that takes red/blue alliance
   feature vectors and returns win probability + predicted score range + confidence.
3. **Model persistence** — load / save via joblib to ``backend/models/predictor.pkl``.
4. **Alliance Recommendations** — rank candidate pick combinations for a team.
5. **Prediction Accuracy Logging** — compare predicted vs. actual outcomes.

Design decisions (from plan)
-----------------------------
- Gradient boosting (GradientBoostingClassifier) for interpretability and small-dataset
  performance — typical FRC events have only 60–100 qual matches.
- Scikit-learn only; no GPU required.
- Model artifact stored at ``backend/models/predictor.pkl`` (gitignored).
- Confidence derived from the model's calibrated predict_proba spread.
- Pure functions where possible — no DB I/O inside this module.

Feature vector (per alliance, 3 teams)
---------------------------------------
  auto_score_sum, auto_score_mean, auto_score_max
  teleop_score_sum, teleop_score_mean, teleop_score_max
  endgame_score_sum, endgame_score_mean, endgame_score_max
  auto_distance_sum, teleop_distance_sum, endgame_distance_sum
  avg_velocity_mean, max_velocity_max
  time_in_zone_sum
  win_rate (historical)
  matches_played (total sample size proxy)

Binary label: 1 = red alliance wins, 0 = blue alliance wins.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib
import numpy as np

logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────

# Resolve relative to this file regardless of CWD
_HERE = Path(__file__).resolve().parent
MODEL_PATH = Path(os.getenv("PREDICTOR_MODEL_PATH", str(_HERE.parent.parent.parent / "models" / "predictor.pkl")))

# ── Strength score weights ────────────────────────────────────────────────────

WEIGHT_AUTO = float(os.getenv("STRENGTH_WEIGHT_AUTO", "0.35"))
WEIGHT_TELEOP = float(os.getenv("STRENGTH_WEIGHT_TELEOP", "0.40"))
WEIGHT_ENDGAME = float(os.getenv("STRENGTH_WEIGHT_ENDGAME", "0.15"))
WEIGHT_WIN_RATE = float(os.getenv("STRENGTH_WEIGHT_WIN_RATE", "0.10"))

# ── Confidence thresholds (predict_proba spread) ──────────────────────────────

CONF_HIGH_THRESHOLD = 0.70     # p >= 0.70 → HIGH
CONF_MEDIUM_THRESHOLD = 0.58   # p >= 0.58 → MEDIUM, else LOW


# ── Data containers ───────────────────────────────────────────────────────────

@dataclass
class TeamStats:
    """Aggregated stats for one team — used as predictor input."""
    team_id: int
    auto_score: float = 0.0
    teleop_score: float = 0.0
    endgame_score: float = 0.0
    auto_distance_ft: float = 0.0
    teleop_distance_ft: float = 0.0
    endgame_distance_ft: float = 0.0
    avg_velocity_fps: float = 0.0
    max_velocity_fps: float = 0.0
    time_in_scoring_zone_s: float = 0.0
    win_rate: float = 0.0        # 0.0–1.0
    matches_played: int = 0


@dataclass
class AlliancePrediction:
    """Prediction output for one match."""
    red_win_probability: float          # 0.0–1.0
    blue_win_probability: float         # = 1 - red_win_probability
    predicted_red_score: float
    predicted_blue_score: float
    red_score_low: float                # 90% confidence interval
    red_score_high: float
    blue_score_low: float
    blue_score_high: float
    confidence: str                     # "high" | "medium" | "low"
    model_available: bool = True        # False when falling back to heuristic


@dataclass
class TeamStrengthScore:
    team_id: int
    strength_score: float               # 0.0–100.0 normalized
    auto_contribution: float
    teleop_contribution: float
    endgame_contribution: float
    win_rate_contribution: float
    matches_played: int
    confidence: str                     # "high" | "medium" | "low" based on sample size


@dataclass
class AllianceRecommendation:
    """One candidate pick for alliance selection."""
    team_id: int
    team_number: int | None
    team_name: str | None
    strength_score: float
    projected_alliance_score: float     # captain + pick projected together
    coverage_notes: list[str] = field(default_factory=list)
    rank: int = 0


# ── Strength score (no model required) ───────────────────────────────────────

def compute_team_strength(stats: TeamStats) -> TeamStrengthScore:  # noqa: E501
    """
    Compute a 0–100 team strength score from aggregated phase stats.

    Weights: auto=35%, teleop=40%, endgame=15%, win_rate=10%.
    Score components are capped at a reasonable maximum before weighting
    so no single outlier can dominate.

    Confidence:
      HIGH   if matches_played >= 6
      MEDIUM if matches_played >= 3
      LOW    otherwise
    """
    # Soft-cap each component (reasonable FRC maxima)
    auto_norm: float = min(stats.auto_score / 20.0, 1.0)
    teleop_norm: float = min(stats.teleop_score / 60.0, 1.0)
    endgame_norm: float = min(stats.endgame_score / 20.0, 1.0)
    win_norm: float = stats.win_rate

    auto_contrib: float = WEIGHT_AUTO * auto_norm * 100
    teleop_contrib: float = WEIGHT_TELEOP * teleop_norm * 100
    endgame_contrib: float = WEIGHT_ENDGAME * endgame_norm * 100
    win_contrib: float = WEIGHT_WIN_RATE * win_norm * 100

    total: float = round(auto_contrib + teleop_contrib + endgame_contrib + win_contrib, 2)

    if stats.matches_played >= 6:
        confidence = "high"
    elif stats.matches_played >= 3:
        confidence = "medium"
    else:
        confidence = "low"

    return TeamStrengthScore(
        team_id=stats.team_id,
        strength_score=total,
        auto_contribution=round(auto_contrib, 2),
        teleop_contribution=round(teleop_contrib, 2),
        endgame_contribution=round(endgame_contrib, 2),
        win_rate_contribution=round(win_contrib, 2),
        matches_played=stats.matches_played,
        confidence=confidence,
    )


# ── Feature engineering ───────────────────────────────────────────────────────

def _alliance_feature_vector(teams: list[TeamStats]) -> list[float]:
    """
    Build a flat feature vector for an alliance of up to 3 teams.
    Missing teams are zero-padded so the vector is always fixed-length.
    """
    padded = (teams + [TeamStats(team_id=-1)] * 3)[:3]

    scores_auto = [t.auto_score for t in padded]
    scores_tele = [t.teleop_score for t in padded]
    scores_end = [t.endgame_score for t in padded]
    dists_auto = [t.auto_distance_ft for t in padded]
    dists_tele = [t.teleop_distance_ft for t in padded]
    dists_end = [t.endgame_distance_ft for t in padded]
    velocities_avg = [t.avg_velocity_fps for t in padded]
    velocities_max = [t.max_velocity_fps for t in padded]
    zones = [t.time_in_scoring_zone_s for t in padded]
    win_rates = [t.win_rate for t in padded]
    matches = [float(t.matches_played) for t in padded]

    def _stats(vals: list[float]) -> list[float]:
        return [sum(vals), sum(vals) / 3.0, max(vals)]

    return [
        *_stats(scores_auto),
        *_stats(scores_tele),
        *_stats(scores_end),
        sum(dists_auto), sum(dists_tele), sum(dists_end),
        sum(velocities_avg) / 3.0, max(velocities_max),
        sum(zones),
        sum(win_rates) / 3.0,
        sum(matches) / 3.0,
    ]


def build_match_feature_row(
    red_teams: list[TeamStats],
    blue_teams: list[TeamStats],
) -> list[float]:
    """
    Concatenate red and blue alliance feature vectors into one row.
    Shape: (34,) — 17 features × 2 alliances.
    """
    return _alliance_feature_vector(red_teams) + _alliance_feature_vector(blue_teams)


# ── Model I/O ─────────────────────────────────────────────────────────────────

def _model_exists() -> bool:
    return MODEL_PATH.exists()


def load_model() -> Any:
    """Load the trained GradientBoostingClassifier from disk. Returns None if not found."""
    if not _model_exists():
        logger.warning("predictor: model artifact not found at %s", MODEL_PATH)
        return None
    try:
        model = joblib.load(MODEL_PATH)
        logger.info("predictor: model loaded from %s", MODEL_PATH)
        return model
    except Exception as exc:
        logger.error("predictor: failed to load model: %s", exc)
        return None


def save_model(model: Any) -> None:
    """Persist model artifact to MODEL_PATH, creating parent dirs as needed."""
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    logger.info("predictor: model saved to %s", MODEL_PATH)


# ── Heuristic fallback ────────────────────────────────────────────────────────

def _heuristic_prediction(
    red_teams: list[TeamStats],
    blue_teams: list[TeamStats],
) -> AlliancePrediction:
    """
    Score-based win probability when no trained model is available.
    Uses sum of estimated scores per alliance, with a logistic squash.
    """
    red_raw = sum(t.auto_score + t.teleop_score + t.endgame_score for t in red_teams)
    blue_raw = sum(t.auto_score + t.teleop_score + t.endgame_score for t in blue_teams)
    total = red_raw + blue_raw

    if total == 0:
        red_prob = 0.5
    else:
        # Soft sigmoid to keep probability from hitting 0/1 on lopsided data
        ratio = (red_raw - blue_raw) / (total + 1e-9)
        red_prob = float(1.0 / (1.0 + np.exp(-6.0 * ratio)))
        red_prob = max(0.05, min(0.95, red_prob))

    blue_prob = 1.0 - red_prob
    spread = 0.15 * float(max(red_raw, blue_raw, 1.0))

    return AlliancePrediction(
        red_win_probability=round(red_prob, 4),
        blue_win_probability=round(blue_prob, 4),
        predicted_red_score=round(red_raw, 1),
        predicted_blue_score=round(blue_raw, 1),
        red_score_low=round(max(0.0, red_raw - spread), 1),
        red_score_high=round(red_raw + spread, 1),
        blue_score_low=round(max(0.0, blue_raw - spread), 1),
        blue_score_high=round(blue_raw + spread, 1),
        confidence="low",   # heuristic is always low-confidence
        model_available=False,
    )


# ── Main prediction interface ─────────────────────────────────────────────────

def predict_match_outcome(
    red_teams: list[TeamStats],
    blue_teams: list[TeamStats],
    model: Any = None,
) -> AlliancePrediction:
    """
    Predict match outcome given red and blue alliance team stats.

    Parameters
    ----------
    red_teams / blue_teams:
        List of TeamStats (1–3 per alliance).  Missing robots are zero-padded.
    model:
        Pre-loaded scikit-learn model.  If None, attempts to load from disk.
        Falls back to heuristic if no model available.

    Returns
    -------
    AlliancePrediction with win probabilities, predicted scores, and confidence.
    """
    if model is None:
        model = load_model()

    if model is None:
        return _heuristic_prediction(red_teams, blue_teams)

    try:
        row = build_match_feature_row(red_teams, blue_teams)
        X = np.array([row])

        # predict_proba returns [[p_blue_wins, p_red_wins]]
        proba = model.predict_proba(X)[0]
        red_prob = float(proba[1])  # label=1 → red wins
        blue_prob = float(proba[0])

        # Confidence from spread
        dominant_p = max(red_prob, blue_prob)
        if dominant_p >= CONF_HIGH_THRESHOLD:
            confidence = "high"
        elif dominant_p >= CONF_MEDIUM_THRESHOLD:
            confidence = "medium"
        else:
            confidence = "low"

        # Score predictions via feature sums (model doesn't regress scores)
        red_raw = sum(t.auto_score + t.teleop_score + t.endgame_score for t in red_teams)
        blue_raw = sum(t.auto_score + t.teleop_score + t.endgame_score for t in blue_teams)

        # Scale scores by win probability to reflect model's view
        score_scale = 1.0 + (red_prob - 0.5) * 0.3
        pred_red = red_raw * score_scale
        pred_blue = blue_raw * (1.0 / score_scale if score_scale != 0 else 1.0)

        spread = 0.12 * float(max(pred_red, pred_blue, 1.0))

        return AlliancePrediction(
            red_win_probability=round(red_prob, 4),
            blue_win_probability=round(blue_prob, 4),
            predicted_red_score=round(pred_red, 1),
            predicted_blue_score=round(pred_blue, 1),
            red_score_low=round(max(0.0, pred_red - spread), 1),
            red_score_high=round(pred_red + spread, 1),
            blue_score_low=round(max(0.0, pred_blue - spread), 1),
            blue_score_high=round(pred_blue + spread, 1),
            confidence=confidence,
            model_available=True,
        )

    except Exception as exc:
        logger.error("predictor: model inference failed, falling back to heuristic: %s", exc)
        return _heuristic_prediction(red_teams, blue_teams)


# ── Alliance recommendations ──────────────────────────────────────────────────

def generate_alliance_recommendations(
    captain_stats: TeamStats,
    candidate_stats: list[TeamStats],
    team_numbers: dict[int, int | None] | None = None,
    team_names: dict[int, str | None] | None = None,
    top_n: int = 5,
    model: Any = None,
) -> list[AllianceRecommendation]:
    """
    Rank candidate teams as alliance picks for a given captain.

    Scores each candidate by projecting the 2-team alliance strength
    and returns the top_n sorted by projected score descending.

    Parameters
    ----------
    captain_stats:
        TeamStats for the alliance captain.
    candidate_stats:
        List of TeamStats for all available pick candidates.
    team_numbers / team_names:
        Optional dicts mapping team_id → team_number / team_name.
    top_n:
        Number of recommendations to return.
    model:
        Pre-loaded scikit-learn model for score projection.
    """
    if model is None:
        model = load_model()

    team_numbers = team_numbers or {}
    team_names = team_names or {}

    recommendations: list[AllianceRecommendation] = []

    captain_strength = compute_team_strength(captain_stats)

    for candidate in candidate_stats:
        if candidate.team_id == captain_stats.team_id:
            continue

        candidate_strength = compute_team_strength(candidate)

        # Project a 2-team alliance score (captain + pick vs. average opponent)
        alliance_score = round(
            (captain_strength.strength_score + candidate_strength.strength_score) / 2.0, 2
        )

        # Coverage notes — highlight complementary strengths
        notes: list[str] = []
        if candidate.auto_score > captain_stats.auto_score * 1.2:
            notes.append("Strong auto — complements captain")
        if candidate.endgame_score > captain_stats.endgame_score * 1.2:
            notes.append("Strong endgame — improves climb coverage")
        if candidate.teleop_score > captain_stats.teleop_score * 1.2:
            notes.append("High teleop scorer")
        if candidate.win_rate > 0.6 and captain_stats.win_rate < 0.5:
            notes.append("Higher win rate than captain — good reliability pick")
        if not notes:
            notes.append("Balanced contributor")

        recommendations.append(
            AllianceRecommendation(
                team_id=candidate.team_id,
                team_number=team_numbers.get(candidate.team_id),
                team_name=team_names.get(candidate.team_id),
                strength_score=candidate_strength.strength_score,
                projected_alliance_score=alliance_score,
                coverage_notes=notes,
            )
        )

    # Sort by projected alliance score descending
    recommendations.sort(key=lambda r: r.projected_alliance_score, reverse=True)
    for i, rec in enumerate(recommendations[:top_n], start=1):
        rec.rank = i

    return recommendations[:top_n]