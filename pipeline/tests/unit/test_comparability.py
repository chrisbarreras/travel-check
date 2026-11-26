"""Comparable itineraries (FR-026)."""

import duckdb
import pytest

from flight_pipeline.compare import comparable_candidates, dep_diff, is_comparable

# (itinerary_id, origin, hub, dest, median_travel_min, median_dep_local_min)
ROWS = [
    ("CMH-ORD-SAN:AA1+AA2", "CMH", "ORD", "SAN", 400, 480),
    ("CMH-DFW-SAN:AA3+AA4", "CMH", "DFW", "SAN", 450, 600),  # +50 travel, +120 dep
    ("CMH-DEN-SAN:UA5+UA6", "CMH", "DEN", "SAN", 461, 480),  # +61 travel: not comparable
    ("CMH-ATL-SAN:DL7+DL8", "CMH", "ATL", "SAN", 400, 661),  # +181 dep: not comparable
    ("CMH-ORD-SEA:AA1+AA9", "CMH", "ORD", "SEA", 400, 480),  # other destination
    ("BOI-ORD-SAN:AA10+AA2", "BOI", "ORD", "SAN", 400, 480),  # other origin
    ("CMH-MSP-SAN:DL11+DL12", "CMH", "MSP", "SAN", 340, 1380),  # 23:00 vs 08:00 -> 540
    ("CMH-CLT-SAN:AA13+AA14", "CMH", "CLT", "SAN", 400, 30),  # 00:30 vs 23:00 -> 90 (midnight)
]


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [(480, 600, 120), (1380, 30, 90), (30, 1380, 90), (0, 720, 720), (100, 100, 0)],
)
def test_departure_difference_is_circular(a: int, b: int, expected: int) -> None:
    assert dep_diff(a, b) == expected


def test_rule() -> None:
    assert is_comparable("CMH", "SAN", 400, 480, "CMH", "SAN", 460, 660, 60, 180)
    assert not is_comparable("CMH", "SAN", 400, 480, "CMH", "SAN", 461, 480, 60, 180)
    assert not is_comparable("CMH", "SAN", 400, 480, "CMH", "SAN", 400, 661, 60, 180)
    assert not is_comparable("CMH", "SAN", 400, 480, "CMH", "SEA", 400, 480, 60, 180)
    assert not is_comparable("CMH", "SAN", 400, 480, "BOI", "SAN", 400, 480, 60, 180)
    assert is_comparable("CMH", "SAN", 340, 1380, "CMH", "SAN", 400, 30, 60, 180)


def test_sql_candidates_match_rule() -> None:
    con = duckdb.connect()
    con.execute(
        "CREATE TABLE it (itinerary_id VARCHAR, origin VARCHAR, hub VARCHAR, dest VARCHAR, "
        "median_travel_min INTEGER, median_dep_local_min INTEGER)"
    )
    con.executemany("INSERT INTO it VALUES (?, ?, ?, ?, ?, ?)", ROWS)
    comparable_candidates(con, "it", 60, 180, "pairs")
    got = con.execute(
        "SELECT itinerary_x, itinerary_y, travel_diff_min, dep_diff_min FROM pairs ORDER BY ALL"
    ).fetchall()
    expected = []
    for i, a in enumerate(ROWS):
        for b in ROWS[i + 1 :]:
            if is_comparable(a[1], a[3], a[4], a[5], b[1], b[3], b[4], b[5], 60, 180):
                x, y = sorted((a, b))
                expected.append((x[0], y[0], abs(a[4] - b[4]), dep_diff(a[5], b[5])))
    assert got == sorted(expected)
    assert ("CMH-ATL-SAN:DL7+DL8", "CMH-CLT-SAN:AA13+AA14", 0, 631) not in got
    assert ("CMH-CLT-SAN:AA13+AA14", "CMH-MSP-SAN:DL11+DL12", 60, 90) in got
    assert ("CMH-DFW-SAN:AA3+AA4", "CMH-ORD-SAN:AA1+AA2", 50, 120) in got


def test_tight_by_median_or_by_share_of_days_below_the_threshold() -> None:
    from flight_pipeline.compare import tight_itineraries
    from flight_pipeline.models import Itinerary
    from tests.unit.test_itineraries import rules as itinerary_rules

    def it(name: str, median: int) -> Itinerary:
        return Itinerary(
            itinerary_id=IDS[name],
            origin="CMH",
            hub="ORD",
            dest="SAN",
            inbound_slot="AA-CMH-ORD-0800",
            outbound_slot=f"AA-ORD-SAN-{IDS[name][-4:]}",
            airline_in="AA",
            airline_out="AA",
            partner_connection=False,
            median_layover_min=median,
            median_travel_min=300,
            median_dep_local_min=480,
            connect_share=1.0,
            eligible_days=300,
            sold_passengers=40,
            routing_itineraries=1,
        )

    IDS = {
        "below": "CMH-ORD-SAN:AA0800+AA1000",
        "at": "CMH-ORD-SAN:AA0800+AA1005",
        "varies": "CMH-ORD-SAN:AA0800+AA1010",
        "steady": "CMH-ORD-SAN:AA0800+AA1015",
    }
    rules = itinerary_rules()  # default minimum 30, no per-hub minimum
    its = [it("below", 40), it("at", 45), it("varies", 60), it("steady", 60)]
    # threshold 30 + 15 = 45; "at" has zero margin on 23% of days, "varies" on 15%
    below = {IDS["at"]: 0.23, IDS["varies"]: 0.15, IDS["steady"]: 0.05}
    assert tight_itineraries(its, rules, 15) == {IDS["below"]}  # the median alone (Phase 0)
    assert tight_itineraries(its, rules, 15, days_below=below, max_day_share=0.1) == {
        IDS["below"],
        IDS["at"],
        IDS["varies"],
    }
