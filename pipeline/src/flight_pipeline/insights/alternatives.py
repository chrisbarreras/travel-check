"""Faster alternatives (research R8, FR-018) and connecting options (research R9, FR-019)."""

from __future__ import annotations

import datetime as dt
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from flight_pipeline.compare import dep_diff, paired_bootstrap, shared_days
from flight_pipeline.showcase.models import Alternative, ConnectingOption, Rate


@dataclass(frozen=True)
class Facts:
    """What the comparisons need about one itinerary."""

    itinerary_id: str
    origin: str
    dest: str
    inbound_slot: str
    outbound_slot: str
    dep_local_min: int
    travel_min: int
    rate: Rate
    days: Mapping[dt.date, bool]  # paired days at the default assumptions: feasible or not


@dataclass(frozen=True)
class Bootstrap:
    resamples: int
    ci_level: float
    seed: int
    min_shared_days: int


def _interval(
    other: Facts, this: Facts, boot: Bootstrap, purpose: str
) -> tuple[float, float, int] | None:
    """The paired interval for rate(other) - rate(this), or None when either rate is
    insufficient or they share too few days."""
    if this.rate.status != "ok" or other.rate.status != "ok":
        return None
    common = shared_days(other.days, this.days)
    if common < boot.min_shared_days:
        return None
    low, high = paired_bootstrap(
        other.days,
        this.days,
        boot.resamples,
        boot.ci_level,
        boot.seed,
        f"{purpose}|{other.itinerary_id}|{this.itinerary_id}",
    )
    if low is None or high is None:
        return None
    return low, high, common


def faster_alternatives(
    this: Facts,
    others: Sequence[Facts],
    *,
    window_min: int,
    min_saving_min: int,
    margin: float,
    boot: Bootstrap,
) -> list[Alternative]:
    """Itineraries on the same route, leaving within the window, at least the minimum saving
    shorter (no travel-time tolerance), whose paired interval for the difference in
    feasibility has a lower bound of at least -margin (non-inferiority). Sorted by minutes
    saved (most first), then by difference, then by id."""
    out: list[tuple[float, Alternative]] = []
    for b in others:
        if b.itinerary_id == this.itinerary_id or (b.origin, b.dest) != (this.origin, this.dest):
            continue
        saved = this.travel_min - b.travel_min
        if saved < min_saving_min or dep_diff(b.dep_local_min, this.dep_local_min) > window_min:
            continue
        ci = _interval(b, this, boot, "faster")
        if ci is None or ci[0] < -margin:
            continue
        rate_this, rate_other = this.rate.rate or 0.0, b.rate.rate or 0.0  # both ok here
        out.append(
            (
                rate_other - rate_this,
                Alternative(
                    itinerary_id=b.itinerary_id,
                    minutes_saved=saved,
                    rate_this=rate_this,
                    rate_other=rate_other,
                    ci_low=ci[0],
                    ci_high=ci[1],
                    shared_days=ci[2],
                ),
            )
        )
    out.sort(key=lambda x: (-x[1].minutes_saved, -x[0], x[1].itinerary_id))
    return [a for _, a in out]


def connecting_options(
    this: Facts,
    others: Sequence[Facts],
    outbound_dep_local_min: Mapping[str, int],
    *,
    boot: Bootstrap,
) -> list[ConnectingOption]:
    """The other outbound flights at the hub that the same inbound flight connected to, to
    the same destination, ranked by rate (rated first, highest first), then by departure.
    ``better`` only when the paired interval for (option - this) is above zero."""
    out: list[ConnectingOption] = []
    for o in others:
        if (
            o.itinerary_id == this.itinerary_id
            or o.inbound_slot != this.inbound_slot
            or o.dest != this.dest
        ):
            continue
        ci = _interval(o, this, boot, "connecting")
        out.append(
            ConnectingOption(
                itinerary_id=o.itinerary_id,
                outbound_dep_local_min=outbound_dep_local_min[o.outbound_slot],
                rate=o.rate,
                better=ci is not None and ci[0] > 0,
                ci_low=ci[0] if ci else None,
                ci_high=ci[1] if ci else None,
            )
        )
    out.sort(
        key=lambda c: (
            c.rate.rate is None,
            -(c.rate.rate or 0.0),
            c.outbound_dep_local_min,
            c.itinerary_id,
        )
    )
    return out
