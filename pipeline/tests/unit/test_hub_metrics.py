"""Candidate pool and candidate metrics (FR-006 to FR-008)."""

import datetime as dt
from typing import Any

import duckdb
import pytest

from flight_pipeline.config import Hubs
from flight_pipeline.hubs import candidate_metrics, candidate_pool, count_eligible


def hubs_cfg(**overrides: Any) -> Hubs:
    base: dict[str, Any] = {
        "candidate_pool_size": 5,
        "airline_share_min": 0.25,
        "eligible_itineraries_min": 1,
        "weights": {"airlines": 1.0, "departures": 1.0, "passengers": 1.0},
        "count": 5,
        "major_networks": ["AA"],
        "winter_months": [12, 1, 2],
        "spring_months": [3, 4, 5],
        "summer_months": [6, 7, 8],
        "autumn_months": [9, 10, 11],
        "min_winter_peak": 0,
        "min_summer_peak": 0,
    }
    base.update(overrides)
    return Hubs.model_validate(base)


def flights_table(con: duckdb.DuckDBPyConnection, rows: list[tuple[Any, ...]]) -> None:
    """rows: (origin, airline, flight_number, service_date, weather_affected, quality_flag)"""
    con.execute(
        "CREATE OR REPLACE TABLE flights (origin VARCHAR, marketing_airline VARCHAR, "
        "flight_number INTEGER, service_date DATE, weather_affected BOOLEAN, quality_flag VARCHAR)"
    )
    con.executemany("INSERT INTO flights VALUES (?, ?, ?, ?, ?, ?)", rows)


JAN, APR, JUL, OCT = (dt.date(2026, m, 1) for m in (1, 4, 7, 10))


def departures(origin: str, airline: str, n: int, day: dt.date, weather: int = 0) -> list[Any]:
    return [(origin, airline, 1000 + i, day, i < weather, "ok") for i in range(n)]


@pytest.fixture
def con() -> duckdb.DuckDBPyConnection:
    c = duckdb.connect()
    rows: list[Any] = []
    # ORD: 10 departures (AA 6, UA 3, DL 1 = 10% < 25% share)
    rows += departures("ORD", "AA", 6, JAN, weather=3) + departures("ORD", "UA", 3, JUL)
    rows += departures("ORD", "DL", 1, OCT)
    # DEN: 8 departures, weather only in July
    rows += departures("DEN", "UA", 4, JUL, weather=2) + departures("DEN", "WN", 4, APR)
    # ATL and CMH tie at 5 departures; ATL wins the last pool slot by airport code
    rows += departures("ATL", "DL", 5, JAN)
    rows += departures("CMH", "AA", 5, JAN)
    # A duplicate copy (flagged) and a conflicting pair do not add departures
    rows += [("ATL", "DL", 1000, JAN, False, "duplicate")]
    rows += [("CMH", "AA", 1000, JAN, False, "conflicting_duplicate")] * 2
    flights_table(c, rows)
    c.execute(
        "CREATE TABLE passengers AS SELECT * FROM (VALUES (2026, 1, 'ORD', 'AA', 500), "
        "(2026, 2, 'ORD', 'UA', 250), (2026, 1, 'DEN', 'UA', 100)) "
        "v(year, month, origin, carrier, passengers)"
    )
    return c


def test_pool_is_top_airports_by_departures_ties_by_code(con: duckdb.DuckDBPyConnection) -> None:
    assert candidate_pool(con, "flights", 3) == ["ORD", "DEN", "ATL"]
    assert candidate_pool(con, "flights", 4) == ["ORD", "DEN", "ATL", "CMH"]


def test_metrics(con: duckdb.DuckDBPyConnection) -> None:
    m = {
        x.airport: x
        for x in candidate_metrics(con, "flights", "passengers", ["ORD", "DEN", "ATL"], hubs_cfg())
    }
    ord_ = m["ORD"]
    assert ord_.departures == 10
    assert ord_.airlines == ["AA", "UA"]  # DL has 10%, below the 25% share
    assert ord_.passengers == 750
    assert ord_.weather_share == pytest.approx(0.3)
    assert ord_.weather_share_by_season.winter == pytest.approx(0.5)  # 3 of 6
    # no weather-affected departures in summer: unknown, not 0% (spec Edge Cases)
    assert ord_.weather_share_by_season.summer is None
    assert ord_.weather_share_by_season.spring is None  # no departures in spring
    assert ord_.weather_peak_season == "winter"
    assert m["DEN"].weather_peak_season == "summer"
    assert m["DEN"].passengers == 100


def test_season_without_weather_is_unknown_peak(con: duckdb.DuckDBPyConnection) -> None:
    m = {x.airport: x for x in candidate_metrics(con, "flights", "passengers", ["ATL"], hubs_cfg())}
    assert m["ATL"].weather_peak_season == "unknown"
    assert m["ATL"].weather_share == 0.0


def test_missing_passengers_is_null(con: duckdb.DuckDBPyConnection) -> None:
    m = {x.airport: x for x in candidate_metrics(con, "flights", "passengers", ["ATL"], hubs_cfg())}
    assert m["ATL"].passengers is None


def test_eligibility_counts_only_origins_outside_pool() -> None:
    con = duckdb.connect()
    con.execute(
        "CREATE TABLE itineraries AS SELECT * FROM (VALUES "
        "('a', 'CMH', 'ORD', 'SAN'), ('b', 'DEN', 'ORD', 'SAN'), ('c', 'BOI', 'ORD', 'DEN'), "
        "('d', 'CMH', 'DEN', 'SAN')) v(itinerary_id, origin, hub, dest)"
    )
    assert count_eligible(con, "itineraries", ["ORD", "DEN"]) == {"ORD": 2, "DEN": 1}
