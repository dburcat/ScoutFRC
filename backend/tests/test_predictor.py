"""
test_predictor.py
=================
Unit tests for Phase 2 Tier 9 — predictor service and prediction tasks.

Runs without a live DB or Redis.  All external dependencies are mocked or
bypassed using simple in-memory data.

Run with:
    pytest backend/tests/test_predictor.py -v
"""

from __future__ import annotations

import math
from unittest.mock import MagicMock, patch

import pytest

from app.services.predictor import (
    TeamStats,
    AlliancePrediction,
    compute_team_strength,
    _alliance_feature_vector,
    build_match_feature_row,
    _heuristic_prediction,
    predict_match_outcome,
    generate_alliance_recommendations,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_team(
    team_id: int = 1,
    auto: float = 10.0,
    teleop: float = 30.0,
    endgame: float = 10.0,
    win_rate: float = 0.5,
    matches: int = 8,
) -> TeamStats:
    return TeamStats(
        team_id=team_id,
        auto_score=auto,
        teleop_score=teleop,
        endgame_score=endgame,
        auto_distance_ft=20.0,
        teleop_distance_ft=80.0,
        endgame_distance_ft=10.0,
        avg_velocity_fps=8.0,
        max_velocity_fps=14.0,
        time_in_scoring_zone_s=15.0,
        win_rate=win_rate,
        matches_played=matches,
    )


# ── Strength score tests ──────────────────────────────────────────────────────

class TestComputeTeamStrength:

    def test_returns_score_between_0_and_100(self):
        stats = _make_team()
        result = compute_team_strength(stats)
        assert 0.0 <= result.strength_score <= 100.0

    def test_higher_scores_produce_higher_strength(self):
        weak = _make_team(auto=2.0, teleop=5.0, endgame=1.0, win_rate=0.1)
        strong = _make_team(auto=18.0, teleop=55.0, endgame=18.0, win_rate=0.9)
        assert compute_team_strength(strong).strength_score > compute_team_strength(weak).strength_score

    def test_contributions_sum_to_total(self):
        stats = _make_team()
        result = compute_team_strength(stats)
        expected = round(
            result.auto_contribution + result.teleop_contribution +
            result.endgame_contribution + result.win_rate_contribution, 2
        )
        assert math.isclose(result.strength_score, expected, abs_tol=0.01)

    def test_confidence_high_with_many_matches(self):
        result = compute_team_strength(_make_team(matches=10))
        assert result.confidence == "high"

    def test_confidence_medium(self):
        result = compute_team_strength(_make_team(matches=4))
        assert result.confidence == "medium"

    def test_confidence_low(self):
        result = compute_team_strength(_make_team(matches=1))
        assert result.confidence == "low"

    def test_zero_stats_gives_zero_score(self):
        stats = TeamStats(team_id=99)
        result = compute_team_strength(stats)
        assert result.strength_score == 0.0

    def test_scores_capped_at_max(self):
        # Even absurdly high scores shouldn't exceed 100
        stats = _make_team(auto=9999, teleop=9999, endgame=9999, win_rate=1.0)
        result = compute_team_strength(stats)
        assert result.strength_score <= 100.0


# ── Feature vector tests ──────────────────────────────────────────────────────

class TestFeatureVectors:

    def test_alliance_vector_length(self):
        teams = [_make_team(team_id=i) for i in range(3)]
        vec = _alliance_feature_vector(teams)
        assert len(vec) == 17  # 3*3 score stats + 3 distances + 2 velocity + 1 zone + 1 win_rate + 1 matches

    def test_alliance_vector_zero_padded_for_fewer_teams(self):
        teams = [_make_team()]  # only 1 team
        vec_one = _alliance_feature_vector(teams)
        teams_three = [_make_team()] + [TeamStats(team_id=-1)] * 2
        vec_three = _alliance_feature_vector(teams_three)
        assert vec_one == vec_three

    def test_match_feature_row_length(self):
        red = [_make_team(team_id=i) for i in range(3)]
        blue = [_make_team(team_id=i + 10) for i in range(3)]
        row = build_match_feature_row(red, blue)
        assert len(row) == 34  # 17 * 2

    def test_match_row_symmetric_teams_gives_equal_halves(self):
        team = _make_team()
        red = [team, team, team]
        blue = [team, team, team]
        row = build_match_feature_row(red, blue)
        assert row[:17] == row[17:]


# ── Heuristic prediction tests ────────────────────────────────────────────────

class TestHeuristicPrediction:

    def test_balanced_teams_give_near_50_50(self):
        red = [_make_team(team_id=1)]
        blue = [_make_team(team_id=2)]
        result = _heuristic_prediction(red, blue)
        assert abs(result.red_win_probability - 0.5) < 0.1
        assert abs(result.blue_win_probability - 0.5) < 0.1

    def test_probabilities_sum_to_1(self):
        red = [_make_team(team_id=1, teleop=50.0)]
        blue = [_make_team(team_id=2, teleop=10.0)]
        result = _heuristic_prediction(red, blue)
        assert math.isclose(result.red_win_probability + result.blue_win_probability, 1.0, abs_tol=1e-6)

    def test_stronger_red_has_higher_win_prob(self):
        strong_red = [_make_team(team_id=1, teleop=55.0)]
        weak_blue = [_make_team(team_id=2, teleop=10.0)]
        result = _heuristic_prediction(strong_red, weak_blue)
        assert result.red_win_probability > result.blue_win_probability

    def test_model_available_is_false(self):
        result = _heuristic_prediction([_make_team()], [_make_team(team_id=2)])
        assert result.model_available is False

    def test_confidence_is_low(self):
        result = _heuristic_prediction([_make_team()], [_make_team(team_id=2)])
        assert result.confidence == "low"

    def test_zero_stats_returns_50_50(self):
        red = [TeamStats(team_id=1)]
        blue = [TeamStats(team_id=2)]
        result = _heuristic_prediction(red, blue)
        assert math.isclose(result.red_win_probability, 0.5, abs_tol=0.01)

    def test_score_bounds_are_non_negative(self):
        red = [_make_team()]
        blue = [_make_team(team_id=2)]
        result = _heuristic_prediction(red, blue)
        assert result.red_score_low >= 0.0
        assert result.blue_score_low >= 0.0


# ── predict_match_outcome tests ───────────────────────────────────────────────

class TestPredictMatchOutcome:

    def test_falls_back_to_heuristic_when_no_model(self):
        with patch("app.services.predictor.load_model", return_value=None):
            red = [_make_team()]
            blue = [_make_team(team_id=2)]
            result = predict_match_outcome(red, blue, model=None)
        assert result.model_available is False

    def test_uses_provided_model(self):
        mock_model = MagicMock()
        mock_model.predict_proba.return_value = [[0.3, 0.7]]
        red = [_make_team()]
        blue = [_make_team(team_id=2)]
        result = predict_match_outcome(red, blue, model=mock_model)
        assert math.isclose(result.red_win_probability, 0.7, abs_tol=0.001)
        assert result.model_available is True

    def test_model_exception_falls_back_to_heuristic(self):
        bad_model = MagicMock()
        bad_model.predict_proba.side_effect = RuntimeError("exploded")
        red = [_make_team()]
        blue = [_make_team(team_id=2)]
        result = predict_match_outcome(red, blue, model=bad_model)
        assert result.model_available is False

    def test_confidence_high_on_dominant_probability(self):
        mock_model = MagicMock()
        mock_model.predict_proba.return_value = [[0.05, 0.95]]
        result = predict_match_outcome([_make_team()], [_make_team(team_id=2)], model=mock_model)
        assert result.confidence == "high"

    def test_confidence_low_on_even_split(self):
        mock_model = MagicMock()
        mock_model.predict_proba.return_value = [[0.51, 0.49]]
        result = predict_match_outcome([_make_team()], [_make_team(team_id=2)], model=mock_model)
        assert result.confidence == "low"


# ── Alliance recommendation tests ─────────────────────────────────────────────

class TestAllianceRecommendations:

    def _make_candidates(self) -> list[TeamStats]:
        return [
            _make_team(team_id=10, auto=5.0,  teleop=15.0, endgame=5.0,  win_rate=0.3),
            _make_team(team_id=11, auto=18.0, teleop=55.0, endgame=15.0, win_rate=0.8),
            _make_team(team_id=12, auto=12.0, teleop=40.0, endgame=18.0, win_rate=0.6),
            _make_team(team_id=13, auto=8.0,  teleop=25.0, endgame=5.0,  win_rate=0.4),
        ]

    def test_returns_correct_count(self):
        captain = _make_team()
        candidates = self._make_candidates()
        recs = generate_alliance_recommendations(captain, candidates, top_n=3)
        assert len(recs) == 3

    def test_sorted_by_projected_score_descending(self):
        captain = _make_team()
        candidates = self._make_candidates()
        recs = generate_alliance_recommendations(captain, candidates, top_n=4)
        scores = [r.projected_alliance_score for r in recs]
        assert scores == sorted(scores, reverse=True)

    def test_ranks_assigned_correctly(self):
        captain = _make_team()
        candidates = self._make_candidates()
        recs = generate_alliance_recommendations(captain, candidates, top_n=3)
        assert [r.rank for r in recs] == [1, 2, 3]

    def test_captain_excluded_from_recommendations(self):
        captain = _make_team(team_id=99)
        candidates = self._make_candidates() + [captain]
        recs = generate_alliance_recommendations(captain, candidates, top_n=10)
        assert all(r.team_id != 99 for r in recs)

    def test_team_numbers_and_names_populated(self):
        captain = _make_team()
        candidates = [_make_team(team_id=10)]
        recs = generate_alliance_recommendations(
            captain, candidates,
            team_numbers={10: 1234},
            team_names={10: "Test Team"},
            top_n=1,
        )
        assert recs[0].team_number == 1234
        assert recs[0].team_name == "Test Team"

    def test_coverage_notes_not_empty(self):
        captain = _make_team()
        candidates = [_make_team(team_id=10, auto=18.0)]  # strong auto
        recs = generate_alliance_recommendations(captain, candidates, top_n=1)
        assert len(recs[0].coverage_notes) > 0

    def test_empty_candidates_returns_empty(self):
        captain = _make_team()
        recs = generate_alliance_recommendations(captain, [], top_n=5)
        assert recs == []

    def test_top_n_larger_than_pool_returns_all(self):
        captain = _make_team()
        candidates = self._make_candidates()
        recs = generate_alliance_recommendations(captain, candidates, top_n=100)
        assert len(recs) == len(candidates)