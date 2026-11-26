"""Showcase curation (specs/002 research R4, FR-007 to FR-010, SC-002)."""

from __future__ import annotations

from typing import Any

import pytest

from flight_pipeline.config import Showcase
from flight_pipeline.curation import CandidateComparison, RouteCandidate, curate


def cfg(**kw: Any) -> Showcase:
    base: dict[str, Any] = {
        "routes_min": 3,
        "routes_max": 4,
        "itineraries_per_route_max": 12,
        "max_share_route": 0.4,
        "max_share_airline": 0.6,
        "max_share_hub": 0.6,
        "regional_share_min": 0.5,
        "cross_hub_share_min": 0.5,
        "size_budget_kb": 2048,
        "landing_budget_kb": 150,
        "output_dir": "site-data/showcase",
        "tight_day_share_max": 0.1,
    }
    base.update(kw)
    return Showcase.model_validate(base)


def route(rid: str, regional: bool = True) -> RouteCandidate:
    o, d = rid.split("-")
    return RouteCandidate(
        route_id=rid, origin=o, dest=d, regional_origin=regional, itinerary_count=4
    )


def comp(
    rid: str,
    n: int,
    diff: float,
    hubs: tuple[str, str],
    airlines: tuple[str, str] = ("DL", "UA"),
    *,
    tight: bool = False,
    settings: int = 9,
) -> CandidateComparison:
    o, d = rid.split("-")
    return CandidateComparison(
        comparison_id=f"{rid}#{n}",
        route_id=rid,
        itinerary_a=f"{o}-{hubs[0]}-{d}:{airlines[0]}{n}",
        itinerary_b=f"{o}-{hubs[1]}-{d}:{airlines[1]}{n}",
        airlines=frozenset(airlines),
        hubs=frozenset(hubs),
        cross_hub=hubs[0] != hubs[1],
        difference=diff,
        settings_compared=settings,
        lower_tight=tight,
    )


def world() -> tuple[list[RouteCandidate], list[CandidateComparison]]:
    routes = [
        route("CMH-SAN"),
        route("BOI-SEA"),
        route("TUL-BOS"),
        route("LGA-MCO", False),
        route("DSM-MIA"),
    ]
    comps = (
        # a dominant market: 10 comparisons, mostly same-hub
        [comp("LGA-MCO", i, 0.30 - i * 0.01, ("ATL", "ATL"), ("DL", "DL")) for i in range(8)]
        + [comp("LGA-MCO", 8, 0.25, ("ATL", "ORD")), comp("LGA-MCO", 9, 0.24, ("ATL", "ORD"))]
        + [
            comp("CMH-SAN", 0, 0.35, ("ORD", "DFW"), ("UA", "AA")),
            comp("CMH-SAN", 1, 0.20, ("ORD", "ORD"), ("UA", "UA")),
        ]
        + [
            comp("BOI-SEA", 0, 0.18, ("DEN", "SEA"), ("UA", "AS")),
            comp("BOI-SEA", 1, 0.40, ("DEN", "SEA"), ("UA", "AS"), tight=True),
        ]
        + [comp("TUL-BOS", 0, 0.15, ("DFW", "ATL"), ("AA", "DL"))]
        + [comp("DSM-MIA", 0, 0.12, ("MSP", "MSP"), ("DL", "DL"))]
    )
    return routes, comps


def test_routes_selected_by_strongest_cross_hub_difference() -> None:
    routes, comps = world()
    result = curate(routes, comps, cfg())
    # BOI-SEA 0.40 (cross-hub), CMH-SAN 0.35, LGA-MCO 0.25 (its 0.30 is same-hub), TUL-BOS 0.15
    assert [r.route_id for r in result.routes] == ["BOI-SEA", "CMH-SAN", "LGA-MCO", "TUL-BOS"]
    assert all(r.rank == i + 1 for i, r in enumerate(result.routes))


def test_route_cap_trims_the_dominant_market() -> None:
    routes, comps = world()
    result = curate(routes, comps, cfg())
    share = {r.route_id: r.share_of_showcase for r in result.routes}
    assert max(share.values()) <= 0.4 + 1e-9
    kept = {c.comparison_id for c in result.comparisons if c.route_id == "LGA-MCO"}
    # trimmed from 10 to a few, keeping its strongest cross-hub comparison
    assert "LGA-MCO#8" in kept
    assert len(kept) < 10


def test_airline_and_hub_caps_hold() -> None:
    routes, comps = world()
    result = curate(routes, comps, cfg())
    assert max(result.airline_shares.values()) <= 0.6 + 1e-9
    assert max(result.hub_shares.values()) <= 0.6 + 1e-9


def test_cross_hub_share_enforced_or_reported() -> None:
    routes, comps = world()
    result = curate(routes, comps, cfg())
    assert result.cross_hub_share >= 0.5
    # DSM-MIA's only comparison is same-hub, so 100% cross-hub cannot be reached
    strict = curate(routes, comps, cfg(cross_hub_share_min=1.0, routes_max=5))
    assert any("cross-hub" in s for s in strict.shortfalls)


def test_regional_share_and_route_count_shortfalls() -> None:
    routes, comps = world()
    assert curate(routes, comps, cfg()).shortfalls == []
    few = curate(routes[:2], [c for c in comps if c.route_id in ("CMH-SAN", "BOI-SEA")], cfg())
    assert any("routes" in s for s in few.shortfalls)
    non_regional = [route(r.route_id, False) for r in routes]
    assert any("regional" in s for s in curate(non_regional, comps, cfg()).shortfalls)


def test_landing_example_is_cross_hub_not_tight_and_compared_everywhere() -> None:
    routes, comps = world()
    result = curate(routes, comps, cfg())
    # BOI-SEA#1 has the largest difference but its lower itinerary is tight
    assert result.landing_comparison_id == "CMH-SAN#0"
    assert "cross-hub" in result.landing_reason
    assert "0.35" in result.landing_reason or "35" in result.landing_reason
    flags = {c.comparison_id: c.landing for c in result.comparisons}
    assert flags["CMH-SAN#0"] is True
    assert sum(flags.values()) == 1


def test_compared_itineraries_per_route_stay_within_the_maximum() -> None:
    routes, comps = world()
    # LGA-MCO's comparisons involve 20 distinct itineraries; allow only 4 per route
    result = curate(routes, comps, cfg(itineraries_per_route_max=4, max_share_route=1.0))
    for r in result.routes:
        mine = {
            x
            for c in result.comparisons
            if c.route_id == r.route_id
            for x in (c.itinerary_a, c.itinerary_b)
        }
        assert len(mine) <= 4


def test_routes_without_a_showcase_comparison_are_not_candidates() -> None:
    routes, comps = world()
    result = curate([*routes, route("ICT-LAS")], comps, cfg(routes_max=12))
    assert "ICT-LAS" not in {r.route_id for r in result.routes}


@pytest.mark.parametrize("_run", range(3))
def test_deterministic(_run: int) -> None:
    routes, comps = world()
    assert curate(routes, comps, cfg()) == curate(
        list(reversed(routes)), list(reversed(comps)), cfg()
    )


def test_repair_removes_pairs_when_one_airline_is_over_and_others_are_at_the_cap() -> None:
    """One removal can never fix AA above half while DL and UA sit at half; removing an AA-DL
    and an AA-UA comparison together does (the real-data case)."""
    from collections.abc import Sequence

    from flight_pipeline.curation import _repair  # pyright: ignore[reportPrivateUsage]

    kept = [
        comp("CMH-SAN", 0, 0.40, ("ORD", "DFW"), ("AA", "DL")),
        comp("CMH-SAN", 1, 0.39, ("ORD", "DFW"), ("AA", "DL")),
        comp("CMH-SAN", 2, 0.38, ("ORD", "DFW"), ("AA", "UA")),
        comp("CMH-SAN", 3, 0.37, ("ORD", "DFW"), ("AA", "UA")),
        comp("CMH-SAN", 4, 0.36, ("ORD", "DFW"), ("AA", "AA")),
        comp("CMH-SAN", 5, 0.35, ("ORD", "DFW"), ("DL", "UA")),
    ]
    rest: list[CandidateComparison] = []

    def violation(cs: Sequence[CandidateComparison]) -> float:
        counts: dict[str, int] = {}
        for c in cs:
            for a in c.airlines:
                counts[a] = counts.get(a, 0) + 1
        return sum(max(0.0, n / len(cs) - 0.5) for n in counts.values()) if cs else 0.0

    _repair(kept, rest, violation, lambda c: True)
    assert violation(kept) == 0
    # two pair removals (AA-DL with AA-UA) leave AA, DL and UA at exactly half
    assert sorted(c.comparison_id for c in kept) == ["CMH-SAN#4", "CMH-SAN#5"]


def test_regional_places_are_not_held_for_candidates_that_do_not_exist() -> None:
    """One regional candidate among many: the other places go to non-regional routes, and
    only the regional share is reported short."""
    routes = [route("CMH-SAN")] + [route(f"L{i:02d}-MCO", False) for i in range(8)]
    comps = [comp("CMH-SAN", 0, 0.30, ("ORD", "DFW"))] + [
        comp(f"L{i:02d}-MCO", 0, 0.20 - i * 0.01, ("ATL", "ORD")) for i in range(8)
    ]
    result = curate(
        routes,
        comps,
        cfg(
            routes_min=3,
            routes_max=6,
            max_share_route=1.0,
            max_share_airline=1.0,
            max_share_hub=1.0,
        ),
    )
    assert len(result.routes) == 6
    assert sum(r.regional_origin for r in result.routes) == 1
    assert result.shortfalls == ["only 1 of 6 routes have a regional origin"]
