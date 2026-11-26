"""Monthly view with disruption notes (research R11, R12, FR-022) and the failure breakdown
(FR-021)."""

from __future__ import annotations

import calendar
import datetime as dt
from collections.abc import Iterable, Mapping, Sequence

from flight_pipeline.config import DisruptionNote
from flight_pipeline.showcase.models import FailureBreakdown, MonthRate

FAILURE_ORDER = ("too_little_time", "cancelled", "diverted")


def failure_breakdown(too_little_time: int, cancelled: int, diverted: int) -> FailureBreakdown:
    """Failed days by type; the dominant type is the largest count (ties in the order too
    little time, cancelled, diverted), or ``none`` without failures."""
    counts = dict(zip(FAILURE_ORDER, (too_little_time, cancelled, diverted), strict=True))
    top = max(counts.values())
    dominant = "none" if top == 0 else next(k for k in FAILURE_ORDER if counts[k] == top)
    return FailureBreakdown(
        too_little_time=too_little_time,
        cancelled=cancelled,
        diverted=diverted,
        dominant=dominant,  # pyright: ignore[reportArgumentType]
    )


def month_key(d: dt.date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def month_bounds(key: str) -> tuple[dt.date, dt.date]:
    y, m = int(key[:4]), int(key[5:])
    return dt.date(y, m, 1), dt.date(y, m, calendar.monthrange(y, m)[1])


def notes_for_month(
    notes: Iterable[DisruptionNote], key: str, airlines: Iterable[str], airports: Iterable[str]
) -> list[str]:
    """Ids of notes whose date range overlaps the month and that name one of the
    itinerary's airlines or airports. Notes are labels only: never used in a calculation."""
    first, last = month_bounds(key)
    carriers, places = set(airlines), set(airports)
    return [
        n.note_id
        for n in notes
        if n.start <= last
        and n.end >= first
        and (carriers & set(n.airlines) or places & set(n.airports))
    ]


def monthly_view(
    months: Sequence[str],
    paired: Mapping[str, tuple[int, int]],
    flown: Iterable[str],
    min_sample: int,
    notes: Sequence[DisruptionNote],
    airlines: Iterable[str],
    airports: Iterable[str],
) -> list[MonthRate]:
    """One entry per period month. ``paired`` maps a month to (paired days, feasible days);
    ``flown`` lists months with any scheduled day of the itinerary (paired or not). A month
    with at least ``min_sample`` paired days shows its rate; otherwise it is insufficient
    data, or no flights when nothing was scheduled."""
    flown_set = set(flown)
    airlines, airports = list(airlines), list(airports)
    out: list[MonthRate] = []
    for key in months:
        n, k = paired.get(key, (0, 0))
        if n >= min_sample:
            status, rate = "ok", round(k / n, 6)
        elif n > 0 or key in flown_set:
            status, rate = "insufficient_data", None
        else:
            status, rate = "no_flights", None
        out.append(
            MonthRate(
                month=key,
                status=status,  # pyright: ignore[reportArgumentType]
                rate=rate,
                paired_days=n,
                note_ids=notes_for_month(notes, key, airlines, airports),
            )
        )
    return out
