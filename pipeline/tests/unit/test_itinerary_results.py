"""Per-itinerary results (User Story 3 scenario 5; FR-023, FR-024)."""

import datetime as dt
import json
from pathlib import Path
from typing import Any

import duckdb
import pytest

from flight_pipeline.feasibility import itinerary_results, lower_percentile
from flight_pipeline.models import ItineraryResult, validate_table

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
EXPECTED = json.loads((FIXTURES / "expected" / "daily_outcomes.json").read_text())
PERIOD = (dt.date(2025, 10, 1), dt.date(2026, 9, 30))
FIELDS = [
    "paired_days",
    "excluded_not_connecting",
    "excluded_quality",
    "count_feasible",
    "count_insufficient_time",
    "count_cancelled",
    "count_diverted",
    "slack_min",
    "slack_p10",
    "slack_p50",
    "slack_p90",
]


def results(con: duckdb.DuckDBPyConnection, min_sample: int) -> dict[str, dict[str, Any]]:
    itinerary_results(con, "classified", "mct30_cut15_rec60", min_sample, PERIOD, "results")
    cur = con.execute("SELECT * FROM results")
    cols = [d[0] for d in cur.description or []]
    return {r[0]: dict(zip(cols, r, strict=True)) for r in cur.fetchall()}


@pytest.mark.parametrize(
    ("values", "q", "expected"),
    [
        ([95, 40, 45, -28, 90], 0.1, -28),
        ([95, 40, 45, -28, 90], 0.5, 45),
        ([95, 40, 45, -28, 90], 0.9, 90),
        ([30] + [125] * 8, 0.9, 125),
        ([7], 0.5, 7),
        ([], 0.5, None),
    ],
)
def test_lower_percentile_rule(values: list[int], q: float, expected: int | None) -> None:
    assert lower_percentile(values, q) == expected


@pytest.mark.parametrize("itinerary", ["CMH-ORD-SAN:AA3100+AA1500", "CMH-ORD-PHX:AA2200+AA2300"])
def test_results_match_hand_computed(con: duckdb.DuckDBPyConnection, itinerary: str) -> None:
    exp = EXPECTED[itinerary]["result"]
    row = results(con, 30)[itinerary]
    assert {f: row[f] for f in FIELDS} == {f: exp[f] for f in FIELDS}


def test_below_minimum_sample_is_insufficient_data_without_rate(
    con: duckdb.DuckDBPyConnection,
) -> None:
    row = results(con, 30)["CMH-ORD-SAN:AA3100+AA1500"]
    assert row["status"] == "insufficient_data"
    assert row["feasibility_rate"] is None


def test_rate_reported_at_or_above_minimum_sample(con: duckdb.DuckDBPyConnection) -> None:
    rows = results(con, 5)
    for itinerary in ("CMH-ORD-SAN:AA3100+AA1500", "CMH-ORD-PHX:AA2200+AA2300"):
        assert rows[itinerary]["status"] == "ok"
        assert rows[itinerary]["feasibility_rate"] == pytest.approx(
            EXPECTED[itinerary]["result"]["rate_if_min_sample_5"], abs=1e-6
        )
    # exactly at the minimum: 8 paired days with min_sample 8 is enough
    at_min = results(con, 8)["CMH-ORD-SAN:AA3100+AA1500"]
    assert at_min["status"] == "ok"
    assert at_min["feasibility_rate"] is not None
    assert results(con, 9)["CMH-ORD-SAN:AA3100+AA1500"]["status"] == "insufficient_data"


def test_every_row_carries_period_and_scenario(con: duckdb.DuckDBPyConnection) -> None:
    for row in results(con, 30).values():
        assert row["period_start"] == PERIOD[0]
        assert row["period_end"] == PERIOD[1]
        assert row["scenario_id"] == "mct30_cut15_rec60"


def test_results_match_model(con: duckdb.DuckDBPyConnection) -> None:
    results(con, 5)
    assert validate_table(con, "results", ItineraryResult) > 0
