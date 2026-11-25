"""Shared unit-test fixtures."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from flight_pipeline.feasibility import classify, daily_slack
from flight_pipeline.itineraries import build_itineraries, build_patterns
from tests.unit.test_itineraries import PERIOD, rules

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.fixture(scope="module")
def con() -> duckdb.DuckDBPyConnection:
    from flight_pipeline.prepare.normalize import normalize_ontime
    from flight_pipeline.providers.timezones import AirportsDataTimezones

    c = duckdb.connect()
    normalize_ontime(
        c, [FIXTURES / "ontime_sample.csv"], AirportsDataTimezones({}), clock_mismatch_max_share=0.2
    )
    from flight_pipeline.prepare.db1b import load_sold_routings

    build_patterns(c, "flights", PERIOD, "patterns")
    load_sold_routings(c, [FIXTURES / "db1b_sample.csv"], {}, "sold")
    build_itineraries(
        c,
        "patterns",
        ["ORD"],
        rules(),
        "itineraries",
        flights="flights",
        sold="sold",
        period=PERIOD,
    )
    daily_slack(c, "flights", "itineraries", rules(), PERIOD, "slack")
    classify(c, "slack", 15, "classified")
    return c
