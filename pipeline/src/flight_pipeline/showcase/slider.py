"""The per-day series behind the transfer-time slider (ADR-0006; specs/002 research R7).

``recompute`` is the calculation the explorer repeats in the browser, specified by
``shared/test-cases/slack-feasibility.json``; ``daily_series`` builds the published columns
from the pipeline's daily outcomes.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from flight_pipeline.models import DailyOutcome
from flight_pipeline.showcase.models import DailySeries

CODES = {"feasible": "F", "insufficient_time": "T", "cancelled": "C", "diverted": "D"}


@dataclass(frozen=True)
class Recomputed:
    paired_days: int
    count_feasible: int
    status: Literal["ok", "insufficient_data"]
    rate: float | None


def rate_of_days(feasible: int, paired: int) -> float:
    """``feasible / paired`` rounded to 6 decimals with halves away from zero, exactly as
    the pipeline's DuckDB ``round`` does (Python's ``round`` rounds halves to even): integer
    arithmetic, so no float error decides a tie."""
    return ((2 * feasible * 10**6 + paired) // (2 * paired)) / 10**6


def recompute(
    slack_min: Sequence[int | None],
    outcome: str,
    transfer_min: int,
    boarding_cutoff_min: int,
    min_sample_days: int,
) -> Recomputed:
    """Feasible days at a given transfer time: code not C or D and slack at least the
    transfer time plus the boarding cutoff."""
    if len(slack_min) != len(outcome):
        raise ValueError("slack_min and outcome must have the same length")
    threshold = transfer_min + boarding_cutoff_min
    feasible = sum(
        1
        for code, slack in zip(outcome, slack_min, strict=True)
        if code not in "CD" and slack is not None and slack >= threshold
    )
    paired = len(slack_min)
    if paired >= min_sample_days and paired > 0:
        return Recomputed(paired, feasible, "ok", rate_of_days(feasible, paired))
    return Recomputed(paired, feasible, "insufficient_data", None)


def daily_series(rows: Sequence[DailyOutcome], period_start: dt.date) -> DailySeries:
    """Columns over one itinerary's paired days, in date order."""
    ordered = sorted(rows, key=lambda r: r.service_date)
    return DailySeries(
        day_offset=[(r.service_date - period_start).days for r in ordered],
        slack_min=[r.raw_slack_min for r in ordered],
        outcome="".join(CODES[r.outcome] for r in ordered),
    )
