"""Daily matching and outcome classification (User Story 3 scenarios 1-4 and 6; FR-019 to
FR-022; ADR-0005)."""

import datetime as dt
import json
from pathlib import Path
from typing import Any

import duckdb
import pytest

from flight_pipeline.feasibility import classify, daily_slack
from flight_pipeline.itineraries import build_itineraries, build_patterns
from flight_pipeline.models import DailyOutcome, validate_table
from tests.unit.test_itineraries import PERIOD, rules

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
EXPECTED = json.loads((FIXTURES / "expected" / "daily_outcomes.json").read_text())


def outcomes(con: duckdb.DuckDBPyConnection, itinerary: str) -> dict[str, dict[str, Any]]:
    rows = con.execute(
        "SELECT service_date, raw_slack_min, outcome FROM classified "
        "WHERE itinerary_id = ? AND status = 'paired' ORDER BY service_date",
        [itinerary],
    ).fetchall()
    return {str(d): {"raw_slack_min": s, "outcome": o} for d, s, o in rows}


@pytest.mark.parametrize("itinerary", ["CMH-ORD-SAN:AA3100+AA1500", "CMH-ORD-PHX:AA2200+AA2300"])
def test_daily_outcomes_match_hand_computed(con: duckdb.DuckDBPyConnection, itinerary: str) -> None:
    assert outcomes(con, itinerary) == EXPECTED[itinerary]["days"]


def test_scenario1_feasible_when_slack_covers_cutoff_plus_connection(
    con: duckdb.DuckDBPyConnection,
) -> None:
    days = outcomes(con, "CMH-ORD-SAN:AA3100+AA1500")
    assert days["2026-01-05"] == {"raw_slack_min": 95, "outcome": "feasible"}
    assert days["2026-01-07"] == {"raw_slack_min": 45, "outcome": "feasible"}  # 45 >= 30 + 15


def test_scenario2_insufficient_time(con: duckdb.DuckDBPyConnection) -> None:
    assert (
        outcomes(con, "CMH-ORD-SAN:AA3100+AA1500")["2026-01-06"]["outcome"] == "insufficient_time"
    )


def test_scenario3_cancellation_of_either_leg(con: duckdb.DuckDBPyConnection) -> None:
    days = outcomes(con, "CMH-ORD-SAN:AA3100+AA1500")
    assert days["2026-01-08"] == {"raw_slack_min": None, "outcome": "cancelled"}  # inbound
    assert days["2026-01-09"] == {"raw_slack_min": None, "outcome": "cancelled"}  # outbound


def test_scenario4_diversion(con: duckdb.DuckDBPyConnection) -> None:
    assert outcomes(con, "CMH-ORD-SAN:AA3100+AA1500")["2026-01-10"]["outcome"] == "diverted"


def test_negative_slack_is_insufficient_time(con: duckdb.DuckDBPyConnection) -> None:
    day = outcomes(con, "CMH-ORD-SAN:AA3100+AA1500")["2026-01-12"]
    assert day == {"raw_slack_min": -28, "outcome": "insufficient_time"}


def test_scenario6_midnight_slack_is_true_elapsed_time(con: duckdb.DuckDBPyConnection) -> None:
    days = outcomes(con, "CMH-ORD-PHX:AA2200+AA2300")
    # inbound lands at 00:00 local after a 95-minute delay; outbound leaves at 00:30 local
    assert days["2026-01-06"] == {"raw_slack_min": 30, "outcome": "insufficient_time"}


def test_excluded_days_counted_by_reason(con: duckdb.DuckDBPyConnection) -> None:
    counts = dict(
        con.execute(
            "SELECT status, count(*) FROM classified "
            "WHERE itinerary_id = 'CMH-ORD-SAN:AA3100+AA1500' GROUP BY 1"
        ).fetchall()
    )
    assert counts == {"paired": 8, "quality": 2}
    counts = dict(
        con.execute(
            "SELECT status, count(*) FROM classified "
            "WHERE itinerary_id = 'CMH-ORD-PHX:AA2200+AA2300' GROUP BY 1"
        ).fetchall()
    )
    assert counts == {"paired": 9, "not_connecting": 1}


def test_cutoff_changes_classification_only(con: duckdb.DuckDBPyConnection) -> None:
    classify(con, "slack", 20, "classified20")
    row = con.execute(
        "SELECT outcome FROM classified20 WHERE itinerary_id = 'CMH-ORD-SAN:AA3100+AA1500' "
        "AND service_date = DATE '2026-01-07'"
    ).fetchone()
    assert row == ("insufficient_time",)  # 45 < 30 + 20


def test_partner_itinerary_uses_partner_connection_time(con: duckdb.DuckDBPyConnection) -> None:
    rows = con.execute(
        "SELECT DISTINCT min_connection_min FROM classified "
        "WHERE itinerary_id = 'CMH-ORD-SEA:AA3100+AS700'"
    ).fetchall()
    assert rows == [(45,)]


def test_paired_rows_match_daily_outcome_model(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        "CREATE OR REPLACE VIEW d AS SELECT itinerary_id, service_date, raw_slack_min, outcome "
        "FROM classified WHERE status = 'paired'"
    )
    assert validate_table(con, "d", DailyOutcome) > 0


@pytest.mark.parametrize(
    ("day", "expected"),
    [(dt.date(2026, 3, 8), 30), (dt.date(2025, 11, 2), 140)],
)
def test_slack_across_daylight_saving_change(
    con: duckdb.DuckDBPyConnection, day: dt.date, expected: int
) -> None:
    build_patterns(con, "flights", (day, day), "dst_patterns")
    build_itineraries(
        con,
        "dst_patterns",
        ["ORD"],
        rules(min_sold_passengers=0),
        "dst_itineraries",
        flights="flights",
        sold="sold",
        period=(day, day),
    )
    daily_slack(con, "flights", "dst_itineraries", rules(), (day, day), "dst_slack")
    row = con.execute(
        "SELECT raw_slack_min FROM dst_slack WHERE itinerary_id LIKE 'CMH-ORD-DEN:WN%'"
    ).fetchone()
    assert row == (expected,)


def test_itinerary_using_both_segments_of_one_flight_number(
    con: duckdb.DuckDBPyConnection,
) -> None:
    day = dt.date(2026, 1, 10)
    build_patterns(con, "flights", (day, day), "seg_patterns")
    build_itineraries(
        con,
        "seg_patterns",
        ["ORD"],
        rules(min_sold_passengers=0),
        "seg_itineraries",
        flights="flights",
        sold="sold",
        period=(day, day),
    )
    daily_slack(con, "flights", "seg_itineraries", rules(), (day, day), "seg_slack")
    row = con.execute(
        "SELECT status, raw_slack_min FROM seg_slack WHERE itinerary_id = 'CMH-ORD-DEN:WN501+WN501'"
    ).fetchone()
    assert row == ("paired", 60)


def test_day_below_scenario_minimum_is_not_connecting_rather_than_failed(
    con: duckdb.DuckDBPyConnection,
) -> None:
    """Documented behavior (methodology, research R6): a scenario's minimum connection time
    also sets the daily matching window, so a day whose scheduled layover is below it is
    excluded as not connecting (that connection would not be sold), not counted as a failure."""
    strict = rules(min_connection_default_min=95)  # itinerary 1 is scheduled at 90 minutes
    daily_slack(con, "flights", "itineraries", strict, PERIOD, "strict_slack")
    statuses = {
        r[0]
        for r in con.execute(
            "SELECT status FROM strict_slack WHERE itinerary_id = 'CMH-ORD-SAN:AA3100+AA1500'"
        ).fetchall()
    }
    assert statuses == {"not_connecting", "quality"}


def test_cancellation_takes_precedence_over_diversion() -> None:
    """FR-021: a day with one leg diverted and the other cancelled is cancelled."""
    c = duckdb.connect()
    c.execute(
        "CREATE TABLE s AS SELECT * FROM (VALUES "
        "('x', DATE '2026-01-05', 'paired', 30, true, true, CAST(NULL AS INTEGER)), "
        "('x', DATE '2026-01-06', 'paired', 30, false, true, CAST(NULL AS INTEGER)), "
        "('x', DATE '2026-01-07', 'paired', 30, true, false, CAST(NULL AS INTEGER))) "
        "t(itinerary_id, service_date, status, min_connection_min, any_cancelled, "
        "any_diverted, raw_slack_min)"
    )
    classify(c, "s", 15, "o")
    assert c.execute("SELECT outcome FROM o ORDER BY service_date").fetchall() == [
        ("cancelled",),
        ("diverted",),
        ("cancelled",),
    ]


def test_outbound_at_the_maximum_layover_connects(con: duckdb.DuckDBPyConnection) -> None:
    """AA1506 leaves exactly 240 minutes after AA3100's scheduled arrival: every inbound day
    connects (FR-015 boundary), matching connect_share 1.0 from the itinerary rules."""
    rows = con.execute(
        "SELECT status, count(*) FROM classified "
        "WHERE itinerary_id = 'CMH-ORD-SAN:AA3100+AA1506' GROUP BY 1 ORDER BY 1"
    ).fetchall()
    assert rows == [("paired", 8), ("quality", 2)]  # d7 and d10 fail quality checks
