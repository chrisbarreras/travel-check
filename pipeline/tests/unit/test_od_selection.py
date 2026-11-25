"""Origin/destination pair ranking and selection (FR-025, FR-018)."""

from typing import Any

from flight_pipeline.config import Selection
from flight_pipeline.od_selection import OdCandidate, pairs_without_itineraries, select_od_pairs

HUBS = {"ORD", "DFW", "DEN", "ATL", "SEA"}


def sel(**overrides: Any) -> Selection:
    base: dict[str, Any] = {"od_pairs_count": 10, "regional_share_min": 0.5, "max_pairs_per_hub": 3}
    base.update(overrides)
    return Selection.model_validate(base)


def cand(
    origin: str, dest: str, comparable: int, hubs: dict[str, int], n: int | None = None
) -> OdCandidate:
    return OdCandidate(
        origin=origin,
        dest=dest,
        itineraries=n if n is not None else sum(hubs.values()),
        comparable_pairs=comparable,
        hub_counts=hubs,
    )


def test_only_pairs_with_two_or_more_itineraries_are_candidates() -> None:
    rows = select_od_pairs(
        [cand("CMH", "SAN", 5, {"ORD": 1}), cand("BOI", "SAN", 1, {"ORD": 2})], HUBS, sel()
    )
    assert [(r.origin, r.dest) for r in rows] == [("BOI", "SAN")]


def test_rank_by_comparable_pairs_then_origin_then_destination() -> None:
    rows = select_od_pairs(
        [
            cand("TUL", "SAN", 3, {"ORD": 2}),
            cand("BOI", "SEA", 3, {"DEN": 2}),
            cand("BOI", "MIA", 3, {"ATL": 2}),
            cand("CMH", "SAN", 9, {"DFW": 3}),
        ],
        HUBS,
        sel(),
    )
    assert [(r.origin, r.dest, r.rank) for r in rows] == [
        ("CMH", "SAN", 1),
        ("BOI", "MIA", 2),
        ("BOI", "SEA", 3),
        ("TUL", "SAN", 4),
    ]


def test_main_hub_is_largest_share_ties_by_code() -> None:
    [row] = select_od_pairs([cand("CMH", "SAN", 1, {"ORD": 2, "DFW": 2, "DEN": 1})], HUBS, sel())
    assert row.main_hub == "DFW"


def test_at_most_n_pairs_per_main_hub() -> None:
    cands = [cand(f"R{i:02d}", "SAN", 20 - i, {"ORD": 2}) for i in range(5)]
    cands += [cand("ZZZ", "SAN", 1, {"DEN": 2})]
    rows = select_od_pairs(cands, HUBS, sel(od_pairs_count=10))
    chosen = [r for r in rows if r.selected]
    assert sum(r.main_hub == "ORD" for r in chosen) == 3
    assert [r.origin for r in rows if r.main_hub == "ORD" and not r.selected] == ["R03", "R04"]
    assert any(r.origin == "ZZZ" and r.selected for r in rows)


def test_at_least_half_regional_origins() -> None:
    # 10 hub-origin pairs rank above 10 regional ones; the selection must still be half regional.
    hub_origins = ["ORD", "DFW", "DEN", "ATL", "SEA"]
    cands = []
    for i, origin in enumerate(hub_origins * 2):
        cands.append(
            cand(origin, f"D{i:02d}", 100 - i, {[h for h in hub_origins if h != origin][i % 4]: 2})
        )
    for i in range(10):
        cands.append(cand(f"R{i:02d}", f"E{i:02d}", 50 - i, {hub_origins[i % 5]: 2}))
    rows = select_od_pairs(cands, HUBS, sel(od_pairs_count=10, max_pairs_per_hub=10))
    chosen = [r for r in rows if r.selected]
    assert len(chosen) == 10
    assert sum(r.regional_origin for r in chosen) == 5
    # the best-ranked 5 hub-origin pairs are kept; the rest of the slots go to regional ones
    assert [r.origin for r in chosen if not r.regional_origin] == hub_origins


def test_regional_flag_uses_selected_hubs() -> None:
    [row] = select_od_pairs([cand("CMH", "SAN", 1, {"ORD": 2})], HUBS, sel())
    assert row.regional_origin
    [row] = select_od_pairs([cand("ORD", "SAN", 1, {"DEN": 2})], HUBS, sel())
    assert not row.regional_origin


def test_selection_deterministic() -> None:
    cands = [cand(f"R{i:02d}", "SAN", i % 3, {"ORD": 2, "DEN": 1}) for i in range(12)]
    assert select_od_pairs(cands, HUBS, sel()) == select_od_pairs(
        list(reversed(cands)), HUBS, sel()
    )


def test_pairs_without_itineraries_reported() -> None:
    assert pairs_without_itineraries([("CMH", "SAN"), ("BOI", "SEA")], {("CMH", "SAN")}) == [
        "BOI-SEA"
    ]
