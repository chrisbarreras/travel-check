"""Hub scoring and constrained selection (User Story 1, FR-009 to FR-012)."""

import json
from pathlib import Path
from typing import Any

import pytest

from flight_pipeline.config import Hubs
from flight_pipeline.hubs import CandidateMetrics, select_hubs
from flight_pipeline.models import SeasonShares

FIXTURE = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "hub_metrics.json").read_text()
)
EXPECTED = FIXTURE["expected"]


def hubs_cfg(**overrides: Any) -> Hubs:
    base: dict[str, Any] = {
        "candidate_pool_size": 10,
        "airline_share_min": 0.05,
        "eligible_itineraries_min": 15,
        "weights": {"airlines": 1.0, "departures": 1.0, "passengers": 1.0},
        "count": 5,
        "major_networks": ["AA", "DL", "UA", "WN", "AS"],
        "winter_months": [12, 1, 2],
        "spring_months": [3, 4, 5],
        "summer_months": [6, 7, 8],
        "autumn_months": [9, 10, 11],
        "min_winter_peak": 2,
        "min_summer_peak": 2,
    }
    base.update(overrides)
    return Hubs.model_validate(base)


def metrics(rows: list[dict[str, Any]] | None = None) -> list[CandidateMetrics]:
    out: list[CandidateMetrics] = []
    for c in rows or FIXTURE["candidates"]:
        shares = {s: None for s in ("winter", "spring", "summer", "autumn")}
        shares[c["peak"]] = c["weather_share"] * 2
        out.append(
            CandidateMetrics(
                airport=c["airport"],
                departures=c["departures"],
                airlines=c["airlines"],
                passengers=c["passengers"],
                weather_share=c["weather_share"],
                weather_share_by_season=SeasonShares(**shares),
                weather_peak_season=c["peak"],
                eligible_itineraries=c["eligible_itineraries"],
            )
        )
    return out


def test_scores_scaled_and_weighted() -> None:
    result = select_hubs(metrics(), hubs_cfg())
    scores = {c.airport: c.score for c in result.candidates}
    assert scores == pytest.approx(EXPECTED["scores"])


def test_rank_ties_broken_by_airport_code() -> None:
    result = select_hubs(metrics(), hubs_cfg())
    assert [c.airport for c in sorted(result.candidates, key=lambda c: c.rank)] == EXPECTED["ranks"]
    # CLT and DEN both score 1.1 (computed in different orders); CLT ranks first.
    ranks = {c.airport: c.rank for c in result.candidates}
    assert ranks["CLT"] == ranks["DEN"] - 1


def test_scenario1_highest_scoring_eligible_selected() -> None:
    result = select_hubs(metrics(), hubs_cfg())
    selected = {s.airport: s.reason for s in result.selection if s.selected}
    assert selected == EXPECTED["selected"]
    assert result.unmet == []


def test_scenario2_network_only_below_cutoff_is_swapped_in() -> None:
    result = select_hubs(metrics(), hubs_cfg())
    reasons = {s.airport: s.reason for s in result.selection}
    assert reasons["SEA"] == "airline_coverage:AS"
    assert reasons["LAS"] is None  # lowest-ranked hub not needed by any constraint


def test_scenario3_weather_season_swap() -> None:
    result = select_hubs(metrics(), hubs_cfg())
    reasons = {s.airport: s.reason for s in result.selection}
    assert reasons["DEN"] == "weather_winter"
    assert reasons["DFW"] is None


def test_scenario4_ineligible_high_scorer_never_selected() -> None:
    result = select_hubs(metrics(), hubs_cfg())
    phx = next(c for c in result.candidates if c.airport == "PHX")
    assert phx.rank == 1
    assert not phx.eligible
    assert not next(s for s in result.selection if s.airport == "PHX").selected


def test_scenario5_unsatisfiable_constraints_reported() -> None:
    result = select_hubs(metrics(), hubs_cfg(min_winter_peak=5))
    assert any(u.startswith("weather_winter") for u in result.unmet)
    assert sum(s.selected for s in result.selection) == 5


def test_network_without_eligible_candidate_is_not_a_constraint() -> None:
    rows = [c for c in FIXTURE["candidates"] if c["airport"] != "SEA"]
    result = select_hubs(metrics(rows), hubs_cfg())
    assert not any("AS" in u for u in result.unmet)


def test_too_few_eligible_candidates_reported() -> None:
    rows = [dict(c, eligible_itineraries=0) for c in FIXTURE["candidates"]]
    rows[1]["eligible_itineraries"] = 99
    result = select_hubs(metrics(rows), hubs_cfg())
    assert sum(s.selected for s in result.selection) == 1
    assert any(u.startswith("hub_count") for u in result.unmet)


def test_missing_passengers_scored_as_zero_but_kept_null() -> None:
    result = select_hubs(metrics(), hubs_cfg())
    sea = next(c for c in result.candidates if c.airport == "SEA")
    assert sea.passengers is None
    assert sea.score == pytest.approx(0.75)


def test_selection_is_deterministic() -> None:
    a = select_hubs(metrics(), hubs_cfg())
    b = select_hubs(list(reversed(metrics())), hubs_cfg())
    assert a == b


def test_every_candidate_has_a_selection_row() -> None:
    result = select_hubs(metrics(), hubs_cfg())
    assert sorted(s.airport for s in result.selection) == sorted(EXPECTED["ranks"])
