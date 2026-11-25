"""Schedule patterns and itinerary rules (ADR-0004, ADR-0013, FR-013 to FR-018a, research R6
and R12).

Covers User Story 2 acceptance scenarios 1-6 (as amended) on the reference fixtures.
"""

import datetime as dt
import json
from pathlib import Path
from typing import Any

import duckdb
import pytest

from flight_pipeline.config import Itineraries
from flight_pipeline.itineraries import build_itineraries, build_patterns
from flight_pipeline.models import FlightPattern, Itinerary, OdExclusions, validate_table
from flight_pipeline.prepare.db1b import load_sold_routings
from flight_pipeline.prepare.normalize import normalize_ontime
from flight_pipeline.providers.timezones import AirportsDataTimezones

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
EXPECTED = json.loads((FIXTURES / "expected" / "itineraries.json").read_text())
PERIOD = (dt.date(2026, 1, 5), dt.date(2026, 1, 14))


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
        c,
        [FIXTURES / "ontime_sample.csv"],
        AirportsDataTimezones({}),
        clock_mismatch_max_share=0.2,
    )
    build_patterns(c, "flights", PERIOD, "patterns")
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
        "patterns",
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


def test_patterns_count_scheduled_days_including_cancellations(
    con: duckdb.DuckDBPyConnection,
) -> None:
    for key, exp in EXPECTED["patterns"].items():
        flight, route = key.split()
        airline, number = flight[:2], int(flight[2:])
        origin, dest = route.split("-")
        row = con.execute(
            "SELECT scheduled_days, recurrence FROM patterns WHERE marketing_airline = ? "
            "AND flight_number = ? AND origin = ? AND dest = ?",
            [airline, number, origin, dest],
        ).fetchone()
        assert row == (exp["scheduled_days"], exp["recurrence"]), key


def test_pattern_table_matches_model(con: duckdb.DuckDBPyConnection) -> None:
    cols = ", ".join(FlightPattern.model_fields)
    con.execute(f"CREATE OR REPLACE VIEW pattern_view AS SELECT {cols} FROM patterns")
    assert validate_table(con, "pattern_view", FlightPattern) > 0


def test_itineraries_match_hand_checked_list(con: duckdb.DuckDBPyConnection) -> None:
    assert build(con) == [i["itinerary_id"] for i in EXPECTED["itineraries"]]
    rows = {
        r[0]: r[1:]
        for r in con.execute(
            "SELECT itinerary_id, partner_connection, median_layover_min, median_travel_min, "
            "median_dep_local_min, connect_share, sold_passengers FROM itineraries"
        ).fetchall()
    }
    for exp in EXPECTED["itineraries"]:
        assert rows[exp["itinerary_id"]] == (
            exp["partner_connection"],
            exp["median_layover_min"],
            exp["median_travel_min"],
            exp["median_dep_local_min"],
            exp["connect_share"],
            exp["sold_passengers"],
        ), exp["itinerary_id"]


def test_itinerary_table_matches_model(con: duckdb.DuckDBPyConnection) -> None:
    build(con)
    assert validate_table(con, "itineraries", Itinerary) == len(EXPECTED["itineraries"])


def test_scenario1_same_marketing_airline_included(con: duckdb.DuckDBPyConnection) -> None:
    assert "CMH-ORD-SAN:AA3100+AA1500" in build(con)


def test_scenario1_routing_below_sold_minimum_excluded(con: duckdb.DuckDBPyConnection) -> None:
    # CMH:ORD:DEN on AA:AA has 12 sampled passengers; the 3-coupon row does not count.
    assert "CMH-ORD-DEN:AA3100+AA1510" not in build(con)
    assert "CMH-ORD-DEN:AA3100+AA1510" in build(con, min_sold_passengers=12)
    assert "CMH-ORD-DEN:AA3100+AA1510" not in build(con, min_sold_passengers=13)


def test_routing_missing_from_db1b_excluded(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("CREATE OR REPLACE TABLE sold_no_sea AS SELECT * FROM sold WHERE dest <> 'SEA'")
    assert "CMH-ORD-SEA:AA3100+AS700" not in build(con, sold="sold_no_sea")


def test_scenario2_same_operator_different_marketing_airlines_excluded(
    con: duckdb.DuckDBPyConnection,
) -> None:
    # A DL:UA ticket is sold, but DL and UA are not partners: never paired.
    assert not any(i.startswith("CMH-ORD-SAN:DL5000") for i in build(con))
    # Listing DL+UA as partners would pair them: the rule is about marketing airlines only.
    assert "CMH-ORD-SAN:DL5000+UA6000" in build(con, partners=[["AA", "AS"], ["DL", "UA"]])


def test_scenario3_partner_pair_labeled_with_partner_minimum(
    con: duckdb.DuckDBPyConnection,
) -> None:
    got = build(con)
    assert "CMH-ORD-SEA:AA3100+AS700" in got  # 70 min
    assert "CMH-ORD-SEA:AA3100+AS702" not in got  # 40 min < 45 partner minimum
    assert "CMH-ORD-SEA:AA3100+AS702" in build(con, min_connection_partner_min=40)
    assert "CMH-ORD-SEA:AA3100+AS700" not in build(con, partners=[])


def test_partner_routing_matched_on_mixed_ticket(con: duckdb.DuckDBPyConnection) -> None:
    build(con)
    assert con.execute(
        "SELECT sold_passengers FROM itineraries WHERE itinerary_id = 'CMH-ORD-SEA:AA3100+AS700'"
    ).fetchone() == (40,)


def test_scenario4_layover_limits(con: duckdb.DuckDBPyConnection) -> None:
    got = build(con)
    assert "CMH-ORD-SAN:AA3100+AA1502" not in got  # 20 min
    assert "CMH-ORD-SAN:AA3100+AA1504" not in got  # 250 min
    assert "CMH-ORD-SAN:AA3100+AA1506" in got  # 240 min, boundary
    assert "CMH-ORD-SAN:AA3100+AA1502" in build(con, min_connection_by_hub={"ORD": 20})
    assert "CMH-ORD-SAN:AA3100+AA1500" not in build(con, min_connection_by_hub={"ORD": 95})


def test_scenario5_recurrence_threshold(con: duckdb.DuckDBPyConnection) -> None:
    got = build(con, min_sold_passengers=10)
    assert "CMH-ORD-DEN:AA3100+AA1508" not in got  # 50% < 60%
    assert "CMH-ORD-DEN:AA3100+AA1510" in got  # 60% including 2 cancelled days
    also = EXPECTED["with_min_sold_10_and_recurrence_0_50_also"]
    assert set(also) <= set(build(con, threshold=0.50, min_sold_passengers=10))
    assert "CMH-ORD-DEN:AA3100+AA1510" not in build(con, threshold=0.75, min_sold_passengers=10)


def test_scenario6_connection_level_recurrence(con: duckdb.DuckDBPyConnection) -> None:
    # Both UA flights run every day (recurrence 1.0) but connect on only 5 of 10 days.
    assert "CMH-ORD-DEN:UA7000+UA7001" not in build(con)
    assert "CMH-ORD-DEN:UA7000+UA7001" in build(con, threshold=0.50)
    assert con.execute(
        "SELECT connect_share FROM itineraries WHERE itinerary_id = 'CMH-ORD-DEN:UA7000+UA7001'"
    ).fetchone() == (0.5,)


def test_connect_share_counts_cancelled_flights_as_scheduled(
    con: duckdb.DuckDBPyConnection,
) -> None:
    build(con, min_sold_passengers=10)
    # AA1510 flies d1-d6 (2 cancelled); AA3100 is cancelled on d4: 6 connecting days of 10.
    assert con.execute(
        "SELECT connect_share, sold_passengers FROM itineraries "
        "WHERE itinerary_id = 'CMH-ORD-DEN:AA3100+AA1510'"
    ).fetchone() == (0.6, 12)


def test_exclusions_follow_rule_order(con: duckdb.DuckDBPyConnection) -> None:
    build(con)
    names = ["candidates", "excluded_layover", "excluded_unsold", "excluded_recurrence"]
    got = {
        f"{r[0]}-{r[1]}": dict(zip([*names, "qualifying"], r[2:], strict=True))
        for r in con.execute(
            "SELECT origin, dest, candidates, excluded_layover, excluded_unsold, "
            "excluded_recurrence, qualifying FROM itineraries_exclusions ORDER BY 1, 2"
        ).fetchall()
    }
    expected = {k: v for k, v in EXPECTED["od_exclusions"].items() if not k.startswith("_")}
    assert got == expected
    assert validate_table(con, "itineraries_exclusions", OdExclusions) == len(expected)


def test_od_pairs_filter_limits_output(con: duckdb.DuckDBPyConnection) -> None:
    assert build(con, od_pairs=[("CMH", "SEA")]) == ["CMH-ORD-SEA:AA3100+AS700"]
    assert con.execute("SELECT origin, dest FROM itineraries_exclusions").fetchall() == [
        ("CMH", "SEA")
    ]


def test_layover_across_local_midnight(con: duckdb.DuckDBPyConnection) -> None:
    assert "CMH-ORD-PHX:AA2200+AA2300" in build(con)


def test_only_given_hubs_used(con: duckdb.DuckDBPyConnection) -> None:
    assert build(con, hubs=["DEN"]) == []


def test_ids_and_order_deterministic(con: duckdb.DuckDBPyConnection) -> None:
    first = con.execute("SELECT * FROM itineraries").fetchall() if build(con) else []
    build(con)
    second = con.execute("SELECT * FROM itineraries").fetchall()
    assert first == second
    assert [r[0] for r in second] == sorted(r[0] for r in second)


def test_layover_and_travel_come_from_daily_schedules_on_connecting_days(
    con: duckdb.DuckDBPyConnection,
) -> None:
    build(con)
    # Pattern medians alone would give 100 min for UA7002 + UA7003 (schedule changes).
    assert con.execute(
        "SELECT median_layover_min, median_travel_min, connect_share FROM itineraries "
        "WHERE itinerary_id = 'CMH-ORD-DEN:UA7002+UA7003'"
    ).fetchone() == (40, 240, 1.0)
    assert con.execute(
        "SELECT median_layover_min, connect_share FROM itineraries "
        "WHERE itinerary_id = 'CMH-ORD-DEN:UA7000+UA7003'"
    ).fetchone() == (40, 0.6)


def test_tight_itineraries_use_their_own_threshold(con: duckdb.DuckDBPyConnection) -> None:
    from flight_pipeline.compare import tight_itineraries
    from flight_pipeline.models import rows_as_dicts

    build(con)
    cur = con.execute("SELECT * FROM itineraries")
    cols = [d[0] for d in cur.description or []]
    its = [Itinerary.model_validate(r) for r in rows_as_dicts(cols, cur.fetchall())]
    # 40 < 30 + 15 (both UA DEN itineraries); AS700 is a partner connection: 70 >= 45 + 15
    assert tight_itineraries(its, rules(), 15) == {
        "CMH-ORD-DEN:UA7000+UA7003",
        "CMH-ORD-DEN:UA7002+UA7003",
    }
    assert "CMH-ORD-SEA:AA3100+AS700" in tight_itineraries(its, rules(), 30)  # 70 < 45 + 30
