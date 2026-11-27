"""Shared slack/feasibility cases (shared/test-cases/slack-feasibility.json, research R7):
the browser calculation and the pipeline's own SQL classification agree with every case."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

import duckdb
import pytest

from flight_pipeline.feasibility import classify, itinerary_results
from flight_pipeline.models import DailyOutcome
from flight_pipeline.showcase.slider import daily_series, recompute

CASES_FILE = (
    Path(__file__).resolve().parents[3] / "shared" / "test-cases" / "slack-feasibility.json"
)
CASES: list[dict[str, Any]] = json.loads(CASES_FILE.read_text(encoding="utf-8"))["cases"]
START = dt.date(2024, 7, 1)


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_browser_calculation_matches_case(case: dict[str, Any]) -> None:
    got = recompute(
        case["slack_min"],
        case["outcome"],
        case["transfer_min"],
        case["boarding_cutoff_min"],
        case["min_sample_days"],
    )
    exp = case["expected"]
    assert (got.paired_days, got.count_feasible, got.status, got.rate) == (
        exp["paired_days"],
        exp["count_feasible"],
        exp["status"],
        exp["rate"],
    )


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_pipeline_calculation_matches_case(case: dict[str, Any]) -> None:
    con = duckdb.connect()
    con.execute("CREATE TABLE it (itinerary_id VARCHAR)")
    con.execute("INSERT INTO it VALUES ('X')")
    con.execute(
        "CREATE TABLE slack (itinerary_id VARCHAR, service_date DATE, status VARCHAR, "
        "min_connection_min INTEGER, any_cancelled BOOLEAN, any_diverted BOOLEAN, "
        "raw_slack_min INTEGER)"
    )
    for i, (code, s) in enumerate(zip(case["outcome"], case["slack_min"], strict=True)):
        con.execute(
            "INSERT INTO slack VALUES ('X', ?, 'paired', ?, ?, ?, ?)",
            [START + dt.timedelta(days=i), case["transfer_min"], code == "C", code == "D", s],
        )
    classify(con, "slack", case["boarding_cutoff_min"], "classified")
    itinerary_results(
        con, "classified", "s", case["min_sample_days"], (START, START), "res", itineraries="it"
    )
    row = con.execute(
        "SELECT paired_days, count_feasible, status, feasibility_rate FROM res"
    ).fetchone()
    exp = case["expected"]
    assert row == (exp["paired_days"], exp["count_feasible"], exp["status"], exp["rate"])


def test_codes_from_the_default_outcomes_are_consistent_with_the_cases() -> None:
    for case in CASES:
        threshold = case["transfer_min"] + case["boarding_cutoff_min"]
        for code, s in zip(case["outcome"], case["slack_min"], strict=True):
            if code in "CD":
                assert s is None
            elif case["name"].startswith("slider"):
                continue  # codes describe the default threshold (45), not the slider's
            else:
                assert (code == "F") == (s >= threshold), case["name"]


def test_daily_series_from_outcomes() -> None:
    rows = [
        DailyOutcome(
            itinerary_id="X",
            service_date=dt.date(2024, 7, 3),
            raw_slack_min=None,
            outcome="cancelled",
        ),
        DailyOutcome(
            itinerary_id="X", service_date=dt.date(2024, 7, 1), raw_slack_min=50, outcome="feasible"
        ),
        DailyOutcome(
            itinerary_id="X",
            service_date=dt.date(2024, 7, 2),
            raw_slack_min=-4,
            outcome="insufficient_time",
        ),
    ]
    s = daily_series(rows, START)
    assert s.day_offset == [0, 1, 2]
    assert s.slack_min == [50, -4, None]
    assert s.outcome == "FTC"
    assert daily_series([], START).outcome == ""


def test_published_series_must_reproduce_the_result() -> None:
    from pydantic import ValidationError

    from flight_pipeline.showcase.models import DailySeries
    from tests.unit.showcase_factory import A, itinerary

    good = itinerary(A, paired=40, feasible=36)
    wrong = DailySeries(day_offset=list(range(40)), slack_min=[60] * 40, outcome="F" * 40)
    with pytest.raises(ValidationError, match="do not match"):
        itinerary(A, paired=40, feasible=36, daily=wrong)
    short = DailySeries(day_offset=[0], slack_min=[60], outcome="F")
    with pytest.raises(ValidationError, match="one entry per paired day"):
        itinerary(A, paired=40, feasible=36, daily=short)
    assert good.daily.outcome.count("F") == 36
