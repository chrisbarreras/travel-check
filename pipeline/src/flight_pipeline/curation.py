"""Showcase curation: routes, balanced comparisons and the landing example
(specs/002 research R4, FR-007 to FR-010, SC-002).

1. Candidate routes are analyzed pairs with at least two itineraries and a showcase
   comparison. Each scores by its strongest cross-hub showcase difference (a route with only
   same-hub comparisons ranks after every cross-hub route), then by its number of showcase
   comparisons, then by route code.
2. Routes are taken in score order up to the maximum, keeping at least the configured share
   of regional origins (outside the candidate pool) when enough exist.
3. Balance caps apply to the showcase comparisons, not to route selection. Each chosen
   route starts with its strongest comparison (cross-hub first, then the larger difference);
   further comparisons are added in strength order whenever the addition does not increase
   the total excess over the route, airline and hub caps and under the cross-hub minimum.
   Caps still exceeded at the end are reported as shortfalls. A comparison counts toward
   both itineraries' airlines and hubs.
4. The landing example is the strongest remaining cross-hub comparison whose lower
   itinerary is not tight and which was compared at every setting.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from flight_pipeline.config import Showcase

_EPS = 1e-9
FULL_SETTINGS = 9


@dataclass(frozen=True)
class RouteCandidate:
    route_id: str
    origin: str
    dest: str
    regional_origin: bool
    itinerary_count: int


@dataclass(frozen=True)
class CandidateComparison:
    comparison_id: str
    route_id: str
    itinerary_a: str
    itinerary_b: str
    airlines: frozenset[str]
    hubs: frozenset[str]
    cross_hub: bool
    difference: float
    settings_compared: int
    lower_tight: bool


@dataclass(frozen=True)
class CuratedRoute:
    route_id: str
    origin: str
    dest: str
    regional_origin: bool
    rank: int
    itinerary_count: int
    comparison_count: int
    share_of_showcase: float


@dataclass(frozen=True)
class CuratedComparison:
    comparison_id: str
    route_id: str
    itinerary_a: str
    itinerary_b: str
    cross_hub: bool
    difference: float
    landing: bool


@dataclass(frozen=True)
class CurationResult:
    routes: list[CuratedRoute]
    comparisons: list[CuratedComparison]
    landing_comparison_id: str | None
    landing_reason: str
    airline_shares: dict[str, float] = field(default_factory=lambda: dict[str, float]())
    hub_shares: dict[str, float] = field(default_factory=lambda: dict[str, float]())
    cross_hub_share: float = 0.0
    shortfalls: list[str] = field(default_factory=lambda: list[str]())


def _score(route_id: str, comps: Sequence[CandidateComparison]) -> tuple[int, float, int, str]:
    mine = [c for c in comps if c.route_id == route_id]
    cross = [c.difference for c in mine if c.cross_hub]
    best = max(cross) if cross else max(c.difference for c in mine)
    return (1 if cross else 0, best, len(mine), route_id)


def _route_order(score: tuple[int, float, int, str]) -> tuple[int, float, int, str]:
    """Sort key, best route first."""
    cross, best, count, route_id = score
    return (-cross, -best, -count, route_id)


def _shares(
    comps: Sequence[CandidateComparison], key: Callable[[CandidateComparison], frozenset[str]]
) -> dict[str, float]:
    total = len(comps)
    counts: dict[str, int] = {}
    for c in comps:
        for k in key(c):
            counts[k] = counts.get(k, 0) + 1
    return {k: round(v / total, 6) for k, v in sorted(counts.items())} if total else {}


def _strength(c: CandidateComparison) -> tuple[bool, float, str]:
    """Sort key, strongest first: cross-hub, then the larger difference, then the id."""
    return (not c.cross_hub, -c.difference, c.comparison_id)


def _repair(
    kept: list[CandidateComparison],
    rest: list[CandidateComparison],
    violation: Callable[[Sequence[CandidateComparison]], float],
    fits: Callable[[CandidateComparison], bool],
) -> None:
    """While the caps or the cross-hub minimum are not met, apply the move that lowers the
    total excess most: add one comparison, or remove one or two (every route keeps at least
    one). Two removals at once are needed when one airline is over its cap and others are at
    theirs: removing a comparison of the first and one each of the others lowers them all.
    Ties prefer adding, then fewer removals, then the stronger comparisons kept. Stops when
    no move lowers the excess; what remains is reported as a shortfall."""
    while (current := violation(kept)) > _EPS:
        order = {c.comparison_id: i for i, c in enumerate(sorted([*kept, *rest], key=_strength))}
        per_route: dict[str, int] = {}
        for c in kept:
            per_route[c.route_id] = per_route.get(c.route_id, 0) + 1
        moves: list[tuple[float, int, int, list[CandidateComparison], list[CandidateComparison]]]
        moves = []
        for c in rest:
            if fits(c):
                moves.append((violation([*kept, c]), 0, order[c.comparison_id], [c], []))
        removable = [c for c in kept if per_route[c.route_id] > 1]
        for i, c in enumerate(removable):
            others = [k for k in kept if k is not c]
            moves.append((violation(others), 1, -order[c.comparison_id], [], [c]))
            for d in removable[i + 1 :]:
                if c.route_id == d.route_id and per_route[c.route_id] < 3:
                    continue
                pair = [k for k in others if k is not d]
                weakest = -(order[c.comparison_id] + order[d.comparison_id])
                moves.append((violation(pair), 2, weakest, [], [c, d]))
        if not moves:
            return
        best = min(moves, key=lambda m: (round(m[0], 9), m[1], m[2]))
        if best[0] >= current - _EPS:
            return
        for c in best[3]:
            kept.append(c)
            rest.remove(c)
        for c in best[4]:
            kept.remove(c)
            rest.append(c)
        rest.sort(key=_strength)


def curate(
    routes: Sequence[RouteCandidate],
    comparisons: Sequence[CandidateComparison],
    cfg: Showcase,
    total_settings: int = FULL_SETTINGS,
) -> CurationResult:
    comps = sorted(comparisons, key=lambda c: c.comparison_id)
    with_comps = {c.route_id for c in comps}
    candidates = sorted(
        (r for r in routes if r.itinerary_count >= 2 and r.route_id in with_comps),
        key=lambda r: _route_order(_score(r.route_id, comps)),
    )
    # places held for regional routes, but never more than there are regional candidates
    required_regional = min(
        math.ceil(cfg.regional_share_min * cfg.routes_max),
        sum(r.regional_origin for r in candidates),
    )
    max_non_regional = cfg.routes_max - required_regional
    chosen: list[RouteCandidate] = []
    non_regional = 0
    for r in candidates:
        if len(chosen) >= cfg.routes_max:
            break
        if not r.regional_origin and non_regional >= max_non_regional:
            continue
        chosen.append(r)
        non_regional += 0 if r.regional_origin else 1

    ids = {r.route_id for r in chosen}
    pool = sorted((c for c in comps if c.route_id in ids), key=_strength)
    shortfalls: list[str] = []

    def per_route(cs: Sequence[CandidateComparison]) -> dict[str, int]:
        out: dict[str, int] = {}
        for c in cs:
            out[c.route_id] = out.get(c.route_id, 0) + 1
        return out

    caps: list[tuple[str, Callable[[CandidateComparison], frozenset[str]], float]] = [
        ("route", lambda c: frozenset({c.route_id}), cfg.max_share_route),
        ("airline", lambda c: c.airlines, cfg.max_share_airline),
        ("hub", lambda c: c.hubs, cfg.max_share_hub),
    ]

    def cross_share(cs: Sequence[CandidateComparison]) -> float:
        return round(sum(c.cross_hub for c in cs) / len(cs), 6) if cs else 0.0

    def violation(cs: Sequence[CandidateComparison]) -> float:
        excess = max(0.0, cfg.cross_hub_share_min - cross_share(cs))
        for _, key, cap in caps:
            excess += sum(max(0.0, s - cap) for s in _shares(cs, key).values())
        return excess

    # seed: every chosen route's strongest comparison; then add comparisons in strength
    # order while an addition does not worsen any cap (repeat until nothing more fits)
    kept: list[CandidateComparison] = []
    for r in chosen:
        kept.append(next(c for c in pool if c.route_id == r.route_id))
    rest = [c for c in pool if c not in kept]

    def fits(c: CandidateComparison) -> bool:
        """The route's compared itineraries stay within the per-route maximum."""
        mine = {x for k in kept if k.route_id == c.route_id for x in (k.itinerary_a, k.itinerary_b)}
        return len(mine | {c.itinerary_a, c.itinerary_b}) <= cfg.itineraries_per_route_max

    def add_while_balanced() -> None:
        added = True
        while added:
            added = False
            for c in rest:
                if fits(c) and violation([*kept, c]) <= violation(kept) + _EPS:
                    kept.append(c)
                    rest.remove(c)
                    added = True
                    break

    add_while_balanced()
    _repair(kept, rest, violation, fits)
    add_while_balanced()

    for name, key, cap in caps:
        for k, s in _shares(kept, key).items():
            if s > cap + _EPS:
                shortfalls.append(f"{name} {k} supplies {s:.0%} of comparisons, above {cap:.0%}")
    if kept and cross_share(kept) < cfg.cross_hub_share_min - _EPS:
        shortfalls.append(
            f"cross-hub comparisons are {cross_share(kept):.0%} of the showcase, "
            f"below {cfg.cross_hub_share_min:.0%}"
        )

    if len(chosen) < cfg.routes_min:
        shortfalls.append(
            f"only {len(chosen)} routes selected, below the minimum of {cfg.routes_min}"
        )
    regional = sum(r.regional_origin for r in chosen)
    if chosen and regional < math.ceil(cfg.regional_share_min * len(chosen)):
        shortfalls.append(f"only {regional} of {len(chosen)} routes have a regional origin")

    landing_pool = [
        c
        for c in kept
        if c.cross_hub and not c.lower_tight and c.settings_compared >= total_settings
    ]
    landing = max(landing_pool, key=lambda c: (c.difference, c.comparison_id), default=None)
    reason = (
        f"strongest cross-hub comparison (+{round(landing.difference * 100)} points, "
        f"{landing.difference:.2f}) whose lower itinerary is not tight and which was compared "
        f"at all {total_settings} settings"
        if landing
        else "no comparison meets the landing rule"
    )
    if landing is None:
        shortfalls.append("no landing example meets the rule")

    counts = per_route(kept)
    total = len(kept)
    curated_routes = [
        CuratedRoute(
            route_id=r.route_id,
            origin=r.origin,
            dest=r.dest,
            regional_origin=r.regional_origin,
            rank=i + 1,
            itinerary_count=r.itinerary_count,
            comparison_count=counts.get(r.route_id, 0),
            share_of_showcase=round(counts.get(r.route_id, 0) / total, 6) if total else 0.0,
        )
        for i, r in enumerate(chosen)
    ]
    curated_comps = [
        CuratedComparison(
            comparison_id=c.comparison_id,
            route_id=c.route_id,
            itinerary_a=c.itinerary_a,
            itinerary_b=c.itinerary_b,
            cross_hub=c.cross_hub,
            difference=c.difference,
            landing=landing is not None and c.comparison_id == landing.comparison_id,
        )
        for c in sorted(kept, key=lambda c: c.comparison_id)
    ]
    return CurationResult(
        routes=curated_routes,
        comparisons=curated_comps,
        landing_comparison_id=landing.comparison_id if landing else None,
        landing_reason=reason,
        airline_shares=_shares(kept, lambda c: c.airlines),
        hub_shares=_shares(kept, lambda c: c.hubs),
        cross_hub_share=cross_share(kept),
        shortfalls=sorted(set(shortfalls)),
    )
