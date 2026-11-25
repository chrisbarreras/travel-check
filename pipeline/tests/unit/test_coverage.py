"""Coverage per airline (FR-005) and regional origins outside the pool (FR-006)."""

from __future__ import annotations

from flight_pipeline.coverage import airline_coverage
from flight_pipeline.od_selection import select_od_pairs
from tests.unit.test_od_selection import HUBS, cand, sel

MAJORS = ["AA", "DL", "UA", "WN", "AS"]


def test_itineraries_and_sold_passengers_per_airline() -> None:
    rows = airline_coverage(["DL", "DL", "AA"], {"DL": 500, "WN": 300, "AA": 40}, MAJORS)
    got = {r.airline: (r.itineraries, r.sold_passengers) for r in rows}
    assert got["DL"] == (2, 500)
    assert got["AA"] == (1, 40)
    assert got["WN"] == (0, 300)
    assert [r.airline for r in rows][:3] == ["DL", "WN", "AA"]  # by sold passengers


def test_major_network_without_itineraries_is_named_with_a_reason() -> None:
    rows = {r.airline: r for r in airline_coverage(["DL"], {"DL": 500, "WN": 300}, MAJORS)}
    assert "sells" in rows["WN"].note  # sold through the hubs, but no regular connection
    assert rows["UA"].itineraries == 0
    assert "no sold" in rows["UA"].note  # nothing sold through the selected hubs
    assert rows["DL"].note == ""


def test_regional_origin_means_outside_the_candidate_pool() -> None:
    pool = [*HUBS, "LGA", "BOS"]
    rows = select_od_pairs(
        [cand("LGA", "SAN", 5, {"ORD": 2}), cand("CMH", "SAN", 4, {"ORD": 2})],
        HUBS,
        sel(),
        pool=pool,
    )
    regional = {(r.origin, r.dest): r.regional_origin for r in rows}
    assert regional[("LGA", "SAN")] is False  # LGA is a large airport in the pool
    assert regional[("CMH", "SAN")] is True
