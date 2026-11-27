"""Nonstop comparison (specs/002 research R3, FR-004)."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import duckdb
import pytest

from flight_pipeline.nonstop import nonstop_medians, nonstop_ratio
from flight_pipeline.prepare.normalize import normalize_ontime
from flight_pipeline.providers.timezones import AirportsDataTimezones

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
PERIOD = (dt.date(2026, 1, 5), dt.date(2026, 1, 14))


@pytest.fixture(scope="module")
def con() -> duckdb.DuckDBPyConnection:
    c = duckdb.connect()
    normalize_ontime(
        c, [FIXTURES / "ontime_sample.csv"], AirportsDataTimezones({}), clock_mismatch_max_share=0.2
    )
    nonstop_medians(c, "flights", PERIOD, "nonstop")
    return c


def test_median_scheduled_nonstop_time_per_pair(con: duckdb.DuckDBPyConnection) -> None:
    # AA4000 CMH->SAN is scheduled at 300 minutes on all 10 days
    assert con.execute(
        "SELECT nonstop_median_min, nonstop_days FROM nonstop WHERE origin = 'CMH' AND dest = 'SAN'"
    ).fetchone() == (300, 10)


def test_pair_without_nonstop_is_absent(con: duckdb.DuckDBPyConnection) -> None:
    # CMH->DEN is only ever flown with a connection in the fixture
    assert con.execute(
        "SELECT count(*) FROM nonstop WHERE origin = 'CMH' AND dest = 'DEN'"
    ).fetchone() == (0,)


def test_any_airline_counts(con: duckdb.DuckDBPyConnection) -> None:
    # CMH->ORD is flown nonstop by AA, DL, UA, WN and F9; all count toward one median
    row = con.execute(
        "SELECT nonstop_median_min FROM nonstop WHERE origin = 'CMH' AND dest = 'ORD'"
    ).fetchone()
    assert row == (80,)


@pytest.mark.parametrize(
    ("travel", "nonstop", "expected"),
    [(440, 300, 1.5), (601, 300, 2.0), (300, None, None), (299, 300, 1.0)],
)
def test_ratio_rounded_to_a_tenth(travel: int, nonstop: int | None, expected: float | None) -> None:
    assert nonstop_ratio(travel, nonstop) == expected
