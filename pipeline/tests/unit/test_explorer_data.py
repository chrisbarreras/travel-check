"""Data the explorer needs (specs/004-explorer-core FR-001, FR-002)."""

from __future__ import annotations

import duckdb
import pytest

from flight_pipeline.providers.airports import MissingAirportError, airport_infos
from flight_pipeline.showcase.assemble import (
    HubTimes,
    SlotTimes,
    hub_schedule,
    hub_times,
    slot_times,
)


def test_airport_infos_from_airportsdata_sorted() -> None:
    infos = airport_infos(["LGA", "LIT", "ATL", "LIT"])
    assert [a.code for a in infos] == ["ATL", "LGA", "LIT"]
    lit = infos[2]
    assert lit.city == "Little Rock"
    assert lit.name
    assert lit.lat == pytest.approx(34.729441)
    assert lit.lon == pytest.approx(-92.224777)


def test_airport_infos_reject_an_unknown_code() -> None:
    with pytest.raises(MissingAirportError, match="ZZZ"):
        airport_infos(["LIT", "ZZZ"])


def test_slot_times_are_medians_over_each_slots_days() -> None:
    con = duckdb.connect()
    con.execute(
        "CREATE TABLE slots_days (slot_id VARCHAR, service_date DATE, marketing_airline VARCHAR,"
        " flight_number VARCHAR, origin VARCHAR, dest VARCHAR, dep_local_min INTEGER)"
    )
    con.execute(
        "CREATE TABLE flights (marketing_airline VARCHAR, flight_number VARCHAR,"
        " service_date DATE, origin VARCHAR, dest VARCHAR, sched_dep_local_min INTEGER,"
        " sched_arr_local_min INTEGER, sched_elapsed_min INTEGER, quality_flag VARCHAR)"
    )
    days = [
        ("2024-07-01", 600, 720, 120),
        ("2024-07-02", 605, 730, 125),
        ("2024-07-03", 610, 725, 115),
    ]
    for i, (day, dep, arr, block) in enumerate(days):
        number = f"DL{i}"  # the slot flies under a different number each day
        con.execute(
            "INSERT INTO slots_days VALUES ('s1', ?, 'DL', ?, 'LIT', 'ATL', ?)", [day, number, dep]
        )
        con.execute(
            "INSERT INTO flights VALUES ('DL', ?, ?, 'LIT', 'ATL', ?, ?, ?, 'ok')",
            [number, day, dep, arr, block],
        )
    # A duplicate record is ignored.
    con.execute(
        "INSERT INTO flights VALUES "
        "('DL', 'DL0', '2024-07-01', 'LIT', 'ATL', 0, 0, 999, 'duplicate')"
    )
    assert slot_times(con, "slots_days", "flights") == {"s1": SlotTimes(arr_local_min=725)}


def test_hub_times_are_medians_over_the_itinerarys_connecting_days() -> None:
    con = duckdb.connect()
    con.execute("CREATE TABLE itineraries (itinerary_id VARCHAR, inbound_slot VARCHAR)")
    con.execute("INSERT INTO itineraries VALUES ('it', 's1')")
    con.execute(
        "CREATE TABLE itinerary_days (itinerary_id VARCHAR, service_date DATE,"
        " match_status VARCHAR, sched_layover_min INTEGER)"
    )
    con.execute(
        "CREATE TABLE slots_days (slot_id VARCHAR, service_date DATE, marketing_airline VARCHAR,"
        " flight_number VARCHAR, origin VARCHAR, dest VARCHAR, dep_local_min INTEGER)"
    )
    con.execute(
        "CREATE TABLE flights (marketing_airline VARCHAR, flight_number VARCHAR,"
        " service_date DATE, origin VARCHAR, dest VARCHAR, sched_dep_local_min INTEGER,"
        " sched_arr_local_min INTEGER, sched_elapsed_min INTEGER, quality_flag VARCHAR)"
    )
    days = [
        ("2024-07-01", "connects", 900, 95),
        ("2024-07-02", "connects", 910, 100),
        ("2024-07-03", "connects", 905, 90),
        # The slot also flies on a day the itinerary did not connect: not counted.
        ("2024-07-04", "not_connecting", 1300, 200),
    ]
    for day, status, arr, block in days:
        con.execute("INSERT INTO itinerary_days VALUES ('it', ?, ?, 60)", [day, status])
        con.execute(
            "INSERT INTO slots_days VALUES ('s1', ?, 'DL', 'DL1', 'LIT', 'ATL', 700)", [day]
        )
        con.execute(
            "INSERT INTO flights VALUES ('DL', 'DL1', ?, 'LIT', 'ATL', 700, ?, ?, 'ok')",
            [day, arr, block],
        )
    assert hub_times(con, "itineraries", "itinerary_days", "slots_days", "flights") == {
        "it": HubTimes(hub_arr_local_min=905, inbound_min=95)
    }


@pytest.mark.parametrize(
    ("hub_arr", "inbound", "layover", "travel", "expected"),
    [
        (913, 95, 99, 327, (1012, 133)),  # LIT-ATL-LGA
        (1400, 60, 99, 300, (59, 141)),  # the hub departure passes midnight
    ],
)
def test_hub_schedule_agrees_with_layover_and_travel(
    hub_arr: int, inbound: int, layover: int, travel: int, expected: tuple[int, int]
) -> None:
    hub_dep, outbound = hub_schedule(hub_arr, inbound, layover, travel)
    assert (hub_dep, outbound) == expected
    assert inbound + layover + outbound == travel
