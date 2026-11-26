"""Faster alternatives (research R8, FR-018) and connecting options (research R9, FR-019)."""

from __future__ import annotations

import datetime as dt

from flight_pipeline.insights.alternatives import (
    Bootstrap,
    Facts,
    connecting_options,
    faster_alternatives,
)
from flight_pipeline.showcase.models import Rate

START = dt.date(2024, 7, 1)
BOOT = Bootstrap(resamples=2000, ci_level=0.95, seed=7, min_shared_days=30)


def days(n: int, failing: set[int] = frozenset(), offset: int = 0) -> dict[dt.date, bool]:  # type: ignore[assignment]
    return {START + dt.timedelta(days=offset + i): i not in failing for i in range(n)}


def facts(
    iid: str,
    *,
    travel: int,
    dep: int = 480,
    inbound: str = "IN1",
    outbound: str | None = None,
    d: dict[dt.date, bool] | None = None,
    dest: str = "SAN",
) -> Facts:
    d = d if d is not None else days(60)
    n, k = len(d), sum(d.values())
    ok = n >= 30
    return Facts(
        itinerary_id=iid,
        origin="CMH",
        dest=dest,
        inbound_slot=inbound,
        outbound_slot=outbound or f"OUT-{iid}",
        dep_local_min=dep,
        travel_min=travel,
        rate=Rate(
            status="ok" if ok else "insufficient_data",
            rate=round(k / n, 6) if ok else None,
            paired_days=n,
            count_feasible=k,
            definition="connection_feasibility",
        ),
        days=d,
    )


def alts(this: Facts, others: list[Facts], margin: float = 0.02, window: int = 180):
    return faster_alternatives(
        this, others, window_min=window, min_saving_min=15, margin=margin, boot=BOOT
    )


def test_equally_reliable_faster_itinerary_is_listed() -> None:
    this = facts("A", travel=400)
    b = facts("B", travel=360)  # same days, all feasible: interval [0, 0]
    [alt] = alts(this, [this, b])
    assert alt.itinerary_id == "B"
    assert alt.minutes_saved == 40
    assert (alt.rate_this, alt.rate_other) == (1.0, 1.0)
    assert (alt.ci_low, alt.ci_high) == (0.0, 0.0)
    assert alt.shared_days == 60


def test_no_travel_time_tolerance_and_minimum_saving() -> None:
    this = facts("A", travel=400)
    far = facts("B", travel=200)  # 200 minutes shorter: listed, the 60-minute cap is lifted
    small = facts("C", travel=390)  # 10 minutes: below the 15-minute minimum
    assert [a.itinerary_id for a in alts(this, [far, small])] == ["B"]


def test_departure_window() -> None:
    this = facts("A", travel=400, dep=480)
    inside = facts("B", travel=360, dep=480 + 180)
    outside = facts("C", travel=360, dep=480 + 181)
    across_midnight = facts("D", travel=360, dep=(480 - 170) % 1440)
    assert [a.itinerary_id for a in alts(this, [inside, outside, across_midnight])] == ["B", "D"]


def test_equivalence_bound_rejects_a_less_reliable_alternative() -> None:
    this = facts("A", travel=400)
    worse = facts("B", travel=360, d=days(60, failing=set(range(0, 60, 4))))  # 75%
    assert alts(this, [worse]) == []
    # a generous margin admits it, and the interval sits below zero
    [alt] = alts(this, [worse], margin=0.5)
    assert alt.ci_high <= 0.0
    assert alt.ci_low >= -0.5


def test_insufficient_data_or_few_shared_days_are_not_compared() -> None:
    this = facts("A", travel=400)
    few = facts("B", travel=360, d=days(20))
    apart = facts("C", travel=360, d=days(60, offset=40))  # 20 shared days
    assert alts(this, [few, apart]) == []


def test_sorted_by_minutes_saved_then_difference() -> None:
    this = facts("A", travel=400, d=days(60, failing={1, 2}))
    b = facts("B", travel=370)
    c = facts("C", travel=340)
    d = facts("D", travel=370, d=days(60, failing={1, 2}))
    assert [a.itinerary_id for a in alts(this, [b, c, d])] == ["C", "B", "D"]


def test_none_applies_is_an_empty_list() -> None:
    this = facts("A", travel=400)
    assert alts(this, []) == []
    assert alts(this, [this]) == []


def test_connecting_options_share_the_inbound_and_rank_by_rate() -> None:
    this = facts("A", travel=400, d=days(60, failing=set(range(0, 60, 3))))  # 2/3
    good = facts("B", travel=430, outbound="OUT-B")  # always feasible
    weak = facts("C", travel=460, outbound="OUT-C", d=days(60, failing=set(range(0, 60, 2))))
    other_inbound = facts("D", travel=400, inbound="IN2")
    other_dest = facts("E", travel=400, dest="LAS")
    thin = facts("F", travel=500, outbound="OUT-F", d=days(10))
    deps = {"OUT-B": 700, "OUT-C": 760, "OUT-F": 820}
    opts = connecting_options(
        this, [this, good, weak, other_inbound, other_dest, thin], deps, boot=BOOT
    )
    assert [o.itinerary_id for o in opts] == ["B", "C", "F"]
    by = {o.itinerary_id: o for o in opts}
    assert by["B"].better
    assert by["B"].ci_low is not None
    assert by["B"].ci_low > 0
    assert not by["C"].better  # lower than this one
    assert not by["F"].better  # insufficient data: no interval
    assert by["F"].ci_low is None
    assert by["F"].rate.status == "insufficient_data"
    assert by["B"].outbound_dep_local_min == 700


def test_better_only_when_the_interval_excludes_zero() -> None:
    this = facts("A", travel=400, d=days(60, failing={5}))
    nearly = facts("B", travel=430, outbound="OUT-B")  # one day better: interval touches 0
    [opt] = connecting_options(this, [nearly], {"OUT-B": 700}, boot=BOOT)
    assert opt.ci_low is not None
    assert opt.ci_low <= 0
    assert not opt.better


def test_no_connecting_options_is_an_empty_list() -> None:
    this = facts("A", travel=400)
    assert connecting_options(this, [this], {}, boot=BOOT) == []
