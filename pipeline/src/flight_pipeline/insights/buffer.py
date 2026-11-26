"""Buffer recommendation (research R10, FR-020)."""

from __future__ import annotations

import math
from collections.abc import Sequence

from flight_pipeline.showcase.models import Buffer


def needed_layover(threshold_min: int, sched_layover_min: int, slack_min: int) -> int:
    """The scheduled layover that would just have met the threshold on one operated day:
    the day's delays are kept, so needed = threshold + scheduled layover - actual slack."""
    return threshold_min + sched_layover_min - slack_min


def buffer(
    operated: Sequence[tuple[int, int]],
    threshold_min: int,
    actual_layover_min: int,
    share: float,
    round_min: int,
) -> Buffer:
    """``operated`` holds (scheduled layover, actual slack) for each operated paired day
    (cancelled and diverted days excluded: no layover helps them). The recommendation is
    the smallest needed layover that covers at least ``share`` of those days (the value at
    position ceil(share * n) in ascending order), rounded up to ``round_min`` minutes, never
    below zero; None without operated days. It covers at least ``share`` of the days, as
    the published wording says ("enough on 95% of operated days")."""
    values = sorted(needed_layover(threshold_min, lay, slack) for lay, slack in operated)
    needed = None
    if values:
        q = values[max(1, math.ceil(round(share * len(values), 9))) - 1]
        needed = max(0, math.ceil(q / round_min) * round_min)
    return Buffer(
        share=share,
        needed_layover_min=needed,
        actual_layover_min=actual_layover_min,
        operated_days=len(values),
    )
