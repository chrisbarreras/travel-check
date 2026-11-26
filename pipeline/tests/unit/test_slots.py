"""Schedule slots (specs/002 research R1, ADR-0014)."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import duckdb
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from flight_pipeline.prepare.normalize import normalize_ontime
from flight_pipeline.providers.timezones import AirportsDataTimezones
from flight_pipeline.slots import SlotRecord, assign_slots, build_slots

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
EXPECTED = json.loads((FIXTURES / "expected" / "slots.json").read_text(encoding="utf-8"))
PERIOD = (dt.date(2026, 1, 5), dt.date(2026, 1, 14))
D0 = dt.date(2026, 1, 5)


def day(n: int) -> dt.date:
    return D0 + dt.timedelta(days=n - 1)


@pytest.fixture(scope="module")
def con() -> duckdb.DuckDBPyConnection:
    c = duckdb.connect()
    normalize_ontime(
        c, [FIXTURES / "ontime_sample.csv"], AirportsDataTimezones({}), clock_mismatch_max_share=0.2
    )
    build_slots(c, "flights", PERIOD, 30, "slots")
    return c


# --- On the reference fixture ------------------------------------------------------------


@pytest.mark.parametrize("slot_id", sorted(EXPECTED["slots"]))
def test_fixture_slots_match_hand_computed(con: duckdb.DuckDBPyConnection, slot_id: str) -> None:
    exp = EXPECTED["slots"][slot_id]
    row = con.execute(
        "SELECT scheduled_days, recurrence, ref_dep_local_min, min_dep_local_min, "
        "max_dep_local_min, flight_numbers FROM slots WHERE slot_id = ?",
        [slot_id],
    ).fetchone()
    assert row is not None, slot_id
    days, rec, ref, lo, hi, numbers = row
    assert (days, rec, ref, lo, hi) == (
        exp["scheduled_days"],
        exp["recurrence"],
        exp["ref"],
        exp["min"],
        exp["max"],
    )
    assert [[n["flight_number"], n["share_of_days"]] for n in numbers] == exp["flight_numbers"]


def test_fixture_joins_recorded_as_changes(con: duckdb.DuckDBPyConnection) -> None:
    got = {
        sid: [[str(d), a, b] for d, a, b in rows]
        for sid, rows in (
            (
                sid,
                con.execute(
                    "SELECT change_date, from_local_min, to_local_min FROM slots_changes "
                    "WHERE slot_id = ? ORDER BY change_date",
                    [sid],
                ).fetchall(),
            )
            for sid in EXPECTED["slots"]
        )
    }
    assert got == {sid: exp["changes"] for sid, exp in EXPECTED["slots"].items()}


def test_every_flight_day_in_exactly_one_slot(con: duckdb.DuckDBPyConnection) -> None:
    dup = con.execute(
        "SELECT count(*) FROM (SELECT slot_id, service_date FROM slots_days GROUP BY ALL "
        "HAVING count(*) > 1)"
    ).fetchone()
    assert dup == (0,)
    multi = con.execute(
        "SELECT count(*) FROM (SELECT marketing_airline, flight_number, origin, dest, "
        "service_date FROM slots_days GROUP BY ALL HAVING count(DISTINCT slot_id) > 1)"
    ).fetchone()
    assert multi == (0,)
    flight_days = con.execute(
        "SELECT count(*) FROM (SELECT DISTINCT marketing_airline, flight_number, origin, dest, "
        "service_date FROM flights WHERE service_date BETWEEN ? AND ?)",
        list(PERIOD),
    ).fetchone()
    assigned = con.execute("SELECT count(*) FROM slots_days").fetchone()
    assert assigned == flight_days


def test_slot_ids_unique_and_deterministic(con: duckdb.DuckDBPyConnection) -> None:
    ids = [r[0] for r in con.execute("SELECT slot_id FROM slots ORDER BY slot_id").fetchall()]
    assert len(ids) == len(set(ids))
    build_slots(con, "flights", PERIOD, 30, "slots_again")
    again = [
        r[0] for r in con.execute("SELECT slot_id FROM slots_again ORDER BY slot_id").fetchall()
    ]
    assert ids == again


# --- The pure assignment ------------------------------------------------------------------


def recs(*items: tuple[int, int, str]) -> list[SlotRecord]:
    return [SlotRecord(day(d), t, f) for d, t, f in items]


def as_sets(slots: list[list[SlotRecord]]) -> list[set[tuple[int, int, str]]]:
    return [{((r.date - D0).days + 1, r.dep_local_min, r.flight_number) for r in s} for s in slots]


def test_gap_clustering_splits_beyond_the_window() -> None:
    got = assign_slots(recs((1, 600, "A1"), (2, 625, "A2"), (3, 660, "A3")), 30)
    assert as_sets([g.records for g in got]) == [
        {(1, 600, "A1"), (2, 625, "A2")},
        {(3, 660, "A3")},
    ]


def test_cluster_wider_than_twice_the_window_is_split_at_its_largest_gap() -> None:
    times = [600, 625, 650, 675, 680]  # chained gaps of 25 and 5; width 80 > 60
    got = assign_slots(recs(*[(i + 1, t, f"A{i}") for i, t in enumerate(times)]), 30)
    assert all(
        max(r.dep_local_min for r in g.records) - min(r.dep_local_min for r in g.records) <= 60
        for g in got
    )
    assert len(got) == 2


def test_same_day_flights_in_one_cluster_are_split_by_rank() -> None:
    got = assign_slots(
        recs(*[(d, 360, "F300") for d in range(1, 4)], *[(d, 380, "F302") for d in range(1, 4)]),
        30,
    )
    assert sorted(g.ref_dep_local_min for g in got) == [360, 380]


def test_lone_flight_goes_to_the_sub_slot_with_its_number() -> None:
    items = [(d, 540, "U7000") for d in range(1, 5)] + [(d, 540, "U7002") for d in (3, 4)]
    got = assign_slots(recs(*items), 30)
    by_number = {frozenset(r.flight_number for r in g.records): g for g in got}
    assert frozenset({"U7000"}) in by_number
    assert len(by_number[frozenset({"U7000"})].records) == 4


def test_schedule_change_with_the_same_number_is_joined() -> None:
    items = [(d, 480, "U7002") for d in range(1, 7)] + [(d, 540, "U7002") for d in range(7, 11)]
    [slot] = assign_slots(recs(*items), 30)
    assert len(slot.records) == 10
    assert slot.changes == [(day(7), 480, 540)]


def test_a_change_and_a_change_back_is_one_slot() -> None:
    # a winter schedule: 08:00, then 07:00 for a while, then 08:00 again (both 08:00 runs
    # fall in one time cluster, around the 07:00 one)
    items = (
        [(d, 480, "U1") for d in range(1, 11)]
        + [(d, 420, "U1") for d in range(11, 21)]
        + [(d, 480, "U1") for d in range(21, 31)]
    )
    [slot] = assign_slots(recs(*items), 30)
    assert len(slot.records) == 30
    assert slot.changes == [(day(11), 480, 420), (day(21), 420, 480)]


def test_a_long_break_inside_one_slot_keeps_it_one_slot() -> None:
    # the same flight paused for two weeks, then back at the same time: one slot, no change
    items = [(d, 480, "U1") for d in range(1, 6)] + [(d, 480, "U1") for d in range(20, 25)]
    [slot] = assign_slots(recs(*items), 30)
    assert len(slot.records) == 10
    assert slot.changes == []


def test_no_join_without_a_shared_number_or_beyond_seven_days() -> None:
    renamed = [(d, 480, "U1") for d in range(1, 5)] + [(d, 540, "U2") for d in range(5, 9)]
    assert len(assign_slots(recs(*renamed), 30)) == 2
    late = [(1, 480, "U1"), (2, 480, "U1"), (11, 540, "U1"), (12, 540, "U1")]
    assert len(assign_slots(recs(*late), 30)) == 2


@settings(max_examples=150, deadline=None)
@given(
    st.lists(
        st.tuples(
            st.integers(min_value=1, max_value=20),
            st.integers(min_value=0, max_value=1439),
            st.sampled_from(["A1", "A2", "A3", "A4"]),
        ),
        min_size=1,
        max_size=60,
    )
)
def test_every_record_in_exactly_one_slot_and_one_per_day(
    items: list[tuple[int, int, str]],
) -> None:
    unique = {(d, f): t for d, t, f in items}  # one record per flight-day
    records = recs(*[(d, t, f) for (d, f), t in unique.items()])
    got = assign_slots(records, 30)
    flat = [r for g in got for r in g.records]
    assert sorted(flat) == sorted(records)
    for g in got:
        dates = [r.date for r in g.records]
        assert len(dates) == len(set(dates))
