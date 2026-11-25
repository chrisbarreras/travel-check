"""Itineraries from schedule slots (ADR-0004, ADR-0013, ADR-0014; specs/002 research R1-R2).

Covers the spec's User Story 1 scenarios and the Phase 0 itinerary rules on the reference
fixtures, now with slot identity, a lossless bound pre-filter and layover limits applied
only through daily matching.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

import duckdb
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from flight_pipeline.config import Itineraries
from flight_pipeline.itineraries import bounds_allow, build_itineraries
from flight_pipeline.models import Itinerary, OdExclusions, validate_table
from flight_pipeline.prepare.db1b import load_sold_routings
from flight_pipeline.prepare.normalize import normalize_ontime
from flight_pipeline.providers.timezones import AirportsDataTimezones
from flight_pipeline.slots import build_slots

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
EXPECTED = json.loads((FIXTURES / "expected" / "itineraries.json").read_text(encoding="utf-8"))
PERIOD = (dt.date(2026, 1, 5), dt.date(2026, 1, 14))
FIELDS = [
    "partner_connection",
    "median_layover_min",
    "median_travel_min",
    "median_dep_local_min",
    "connect_share",
    "eligible_days",
    "sold_passengers",
    "routing_itineraries",
]


def rules(**overrides: Any) -> Itineraries:
    base: dict[str, Any] = {
        "min_connection_default_min": 30,
        "min_connection_partner_min": 45,
        "min_connection_by_hub": {},
        "max_layover_min": 240,
        "recurrence_threshold": 0.60,
        "partners": [["AA", "AS"]],
        "min_sold_passengers": 30,
        "carrier_map": {},
        "identity": "schedule",
        "slot_window_min": 30,
    }
    base.update(overrides)
    return Itineraries.model_validate(base)


@pytest.fixture(scope="module")
def con() -> duckdb.DuckDBPyConnection:
    c = duckdb.connect()
    normalize_ontime(
        c, [FIXTURES / "ontime_sample.csv"], AirportsDataTimezones({}), clock_mismatch_max_share=0.2
    )
    build_slots(c, "flights", PERIOD, 30, "slots")
    load_sold_routings(c, [FIXTURES / "db1b_sample.csv"], {}, "sold")
    return c


def ids(con: duckdb.DuckDBPyConnection, table: str = "itineraries") -> list[str]:
    return [r[0] for r in con.execute(f"SELECT itinerary_id FROM {table} ORDER BY 1").fetchall()]


def build(
    con: duckdb.DuckDBPyConnection,
    *,
    hubs: list[str] | None = None,
    threshold: float | None = None,
    sold: str = "sold",
    od_pairs: list[tuple[str, str]] | None = None,
    **rule_overrides: Any,
) -> list[str]:
    build_itineraries(
        con,
        "slots",
        hubs or ["ORD"],
        rules(**rule_overrides),
        "itineraries",
        threshold,
        flights="flights",
        sold=sold,
        period=PERIOD,
        od_pairs=od_pairs,
    )
    return ids(con)


def test_itineraries_match_hand_checked_list(con: duckdb.DuckDBPyConnection) -> None:
    assert build(con) == [i["itinerary_id"] for i in EXPECTED["itineraries"]]
    rows = {
        r[0]: r[1:]
        for r in con.execute(
            f"SELECT itinerary_id, {', '.join(FIELDS)} FROM itineraries"
        ).fetchall()
    }
    for exp in EXPECTED["itineraries"]:
        assert rows[exp["itinerary_id"]] == tuple(exp[f] for f in FIELDS), exp["itinerary_id"]


def test_itinerary_table_matches_model(con: duckdb.DuckDBPyConnection) -> None:
    build(con)
    assert validate_table(con, "itineraries", Itinerary) == len(EXPECTED["itineraries"])


def test_renumbering_airline_forms_one_itinerary(con: duckdb.DuckDBPyConnection) -> None:
    # US1 scenario 1: WN changes flight numbers every day but keeps the schedule.
    assert "CMH-ORD-DEN:WN1000+WN1200" in build(con)


def test_schedule_changes_do_not_break_an_itinerary(con: duckdb.DuckDBPyConnection) -> None:
    # US1 scenario 2: both UA legs change schedule at different times; the layover is checked
    # per day, and the median comes from the connecting days (40), not the slots' medians.
    build(con)
    row = con.execute(
        "SELECT median_layover_min, connect_share FROM itineraries "
        "WHERE itinerary_id = 'CMH-ORD-DEN:UA0800+UA1000'"
    ).fetchone()
    assert row == (40, 1.0)


def test_end_of_period_day_is_excluded_not_counted(con: duckdb.DuckDBPyConnection) -> None:
    build(con)
    assert con.execute(
        "SELECT connect_share, eligible_days FROM itineraries "
        "WHERE itinerary_id = 'CMH-ORD-PHX:AA2200+AA0030'"
    ).fetchone() == (1.0, 9)


def test_same_operator_different_marketing_airlines_never_paired(
    con: duckdb.DuckDBPyConnection,
) -> None:
    assert not any(i.startswith("CMH-ORD-SAN:DL") for i in build(con))
    assert "CMH-ORD-SAN:DL0700+UA0830" in build(con, partners=[["AA", "AS"], ["DL", "UA"]])


def test_partner_minimum(con: duckdb.DuckDBPyConnection) -> None:
    got = build(con)
    assert "CMH-ORD-SEA:AA0800+AS0930" in got
    assert "CMH-ORD-SEA:AA0800+AS0900" not in got
    assert "CMH-ORD-SEA:AA0800+AS0900" in build(con, min_connection_partner_min=40)
    assert "CMH-ORD-SEA:AA0800+AS0930" not in build(con, partners=[])


def test_layover_limits_per_day(con: duckdb.DuckDBPyConnection) -> None:
    got = build(con)
    assert "CMH-ORD-SAN:AA0800+AA0840" not in got  # 20 min
    assert "CMH-ORD-SAN:AA0800+AA1230" not in got  # 250 min
    assert "CMH-ORD-SAN:AA0800+AA1220" in got  # 240 min, boundary
    assert "CMH-ORD-SAN:AA0800+AA0840" in build(con, min_connection_by_hub={"ORD": 20})
    assert "CMH-ORD-SAN:AA0800+AA0950" not in build(con, min_connection_by_hub={"ORD": 95})


def test_sold_routing_minimum(con: duckdb.DuckDBPyConnection) -> None:
    assert "CMH-ORD-DEN:AA0800+AA1030" not in build(con)
    build(con, min_sold_passengers=10)
    row = con.execute(
        "SELECT connect_share, median_layover_min FROM itineraries "
        "WHERE itinerary_id = 'CMH-ORD-DEN:AA0800+AA1030'"
    ).fetchone()
    exp = EXPECTED["with_min_sold_10_also"]["CMH-ORD-DEN:AA0800+AA1030"]
    assert row == (exp["connect_share"], exp["median_layover_min"])


def test_connection_level_recurrence(con: duckdb.DuckDBPyConnection) -> None:
    assert "CMH-ORD-DEN:UA0900+UA1000" in build(con)
    assert "CMH-ORD-DEN:UA0900+UA1000" not in build(con, threshold=0.75)
    row = con.execute(
        "SELECT excluded_recurrence FROM itineraries_exclusions WHERE origin = 'CMH' "
        "AND dest = 'DEN'"
    ).fetchone()
    assert row is not None
    assert row[0] >= 1


def test_exclusions_follow_rule_order(con: duckdb.DuckDBPyConnection) -> None:
    build(con)
    names = [
        "candidates",
        "excluded_bounds",
        "excluded_unsold",
        "excluded_not_connecting",
        "excluded_recurrence",
        "qualifying",
    ]
    got = {
        f"{r[0]}-{r[1]}": dict(zip(names, r[2:], strict=True))
        for r in con.execute(
            f"SELECT origin, dest, {', '.join(names)} FROM itineraries_exclusions ORDER BY 1, 2"
        ).fetchall()
    }
    expected = {k: v for k, v in EXPECTED["od_exclusions"].items() if not k.startswith("_")}
    assert got == expected
    assert validate_table(con, "itineraries_exclusions", OdExclusions) == len(expected)


def test_od_pairs_filter(con: duckdb.DuckDBPyConnection) -> None:
    assert build(con, od_pairs=[("CMH", "SEA")]) == ["CMH-ORD-SEA:AA0800+AS0930"]


def test_only_given_hubs(con: duckdb.DuckDBPyConnection) -> None:
    assert build(con, hubs=["DEN"]) == []


def test_deterministic(con: duckdb.DuckDBPyConnection) -> None:
    build(con)
    first = con.execute("SELECT * FROM itineraries ORDER BY itinerary_id").fetchall()
    build(con)
    assert con.execute("SELECT * FROM itineraries ORDER BY itinerary_id").fetchall() == first


# --- The bound pre-filter is lossless ----------------------------------------------------


@settings(max_examples=300, deadline=None)
@given(
    arr=st.lists(st.integers(0, 1439), min_size=1, max_size=4),
    dep=st.lists(st.integers(0, 1439), min_size=1, max_size=4),
    min_conn=st.integers(20, 60),
    max_lay=st.integers(120, 300),
)
def test_bounds_never_drop_a_pair_that_can_connect(
    arr: list[int], dep: list[int], min_conn: int, max_lay: int
) -> None:
    # A real day's layover is a local-time difference shifted by at most 60 min on a
    # daylight-saving night; if any such day can lie within the limits, the bound keeps it.
    for a in arr:
        for d in dep:
            for shift in (-60, 0, 60):
                layover = (d - a) % 1440 + shift
                if min_conn <= layover <= max_lay:
                    assert bounds_allow(arr, dep, min_conn, max_lay)


def test_bounds_drop_a_pair_that_cannot_connect() -> None:
    assert not bounds_allow([1345], [590], 30, 240)  # 685 min at best
    assert bounds_allow([500], [590], 30, 240)
