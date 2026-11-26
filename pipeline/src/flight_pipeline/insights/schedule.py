"""Schedule-pattern warnings (research R13, FR-023) and Find-this-itinerary parameters
(research R14, FR-024)."""

from __future__ import annotations

import datetime as dt
from collections import Counter
from collections.abc import Sequence
from typing import Literal

from flight_pipeline.compare import dep_diff
from flight_pipeline.showcase.models import FindLeg, FindParams, ScheduleChange, ScheduleWarnings


def _mode(counts: Counter[int]) -> int:
    """Most frequent value; ties go to the smaller minute."""
    return min(counts, key=lambda v: (-counts[v], v))


def schedule_changes(
    days: Sequence[tuple[dt.date, int]],
    joins: Sequence[tuple[dt.date, int, int]],
    leg: Literal["inbound", "outbound"],
    *,
    min_shift_min: int,
    min_days: int,
) -> list[ScheduleChange]:
    """Lasting changes in one leg's scheduled local departure time. ``days`` holds (date,
    local departure minute) for each scheduled day of the slot. A change is a date from
    which the time differs from the modal value since the previous change by at least
    ``min_shift_min`` and stays at the new value for at least ``min_days`` consecutive
    scheduled days. Every slot join of research R1 step 4 (``joins``: date, from, to) is a
    change whatever its length. Sorted by date."""
    ordered = sorted(days)
    found: dict[dt.date, ScheduleChange] = {}
    counts: Counter[int] = Counter()
    i = 0
    while i < len(ordered):
        date, minute = ordered[i]
        if counts:
            current = _mode(counts)
            run = ordered[i : i + min_days]
            if (
                dep_diff(minute, current) >= min_shift_min
                and len(run) == min_days
                and all(m == minute for _, m in run)
            ):
                found[date] = ScheduleChange(
                    date=date, leg=leg, from_local_min=current, to_local_min=minute
                )
                counts = Counter()
        counts[minute] += 1
        i += 1
    for date, before, after in joins:
        found.setdefault(
            date, ScheduleChange(date=date, leg=leg, from_local_min=before, to_local_min=after)
        )
    return [found[d] for d in sorted(found)]


def schedule_warnings(
    connect_share: float,
    eligible_days: int,
    inbound: Sequence[ScheduleChange],
    outbound: Sequence[ScheduleChange],
) -> ScheduleWarnings:
    """Changes on either leg by date, with the connection share and its sample. The share is
    connecting days / eligible days rounded to 6 decimals, which recovers the count exactly
    for any period of up to 366 days."""
    changes = sorted([*inbound, *outbound], key=lambda c: (c.date, c.leg))
    return ScheduleWarnings(
        connect_share=connect_share,
        connecting_days=round(connect_share * eligible_days),
        eligible_days=eligible_days,
        changes=changes,
    )


def find_params(
    origin: str,
    dest: str,
    airlines: Sequence[str],
    legs: Sequence[Sequence[tuple[str, float]]],
) -> FindParams:
    """For each leg, the flight number flown on most days with its share (``legs`` holds each
    leg's flight numbers sorted by share, most first). The pipeline builds no URLs."""
    out: list[FindLeg] = []
    for numbers in legs:
        number, share = min(numbers, key=lambda x: (-x[1], x[0])) if numbers else ("", 0.0)
        out.append(FindLeg(flight_number=number, share_of_days=share))
    return FindParams(origin=origin, dest=dest, airlines=sorted(set(airlines)), legs=out)
