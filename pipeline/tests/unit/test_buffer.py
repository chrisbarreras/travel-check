"""Buffer recommendation (research R10, FR-020)."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from flight_pipeline.insights.buffer import buffer, needed_layover


def test_needed_layover_keeps_the_days_delays() -> None:
    # threshold 45, scheduled 90, actual slack 70 (inbound 20 minutes late): needed 65
    assert needed_layover(45, 90, 70) == 65
    # outbound left 10 minutes late: slack 100, needed 35
    assert needed_layover(45, 90, 100) == 35


def test_smallest_value_covering_the_share_rounded_up_to_five() -> None:
    # 20 operated days, scheduled 90, threshold 45; needed = 135 - slack
    slacks = [100] * 18 + [60, 20]  # needed: 35 x18, 75, 115
    b = buffer([(90, s) for s in slacks], 45, 90, 0.95, 5)
    # sorted needed: 35 x18, 75, 115; position ceil(0.95 * 20) = 19 -> 75, enough on 19 of 20
    assert b.needed_layover_min == 75
    assert b.actual_layover_min == 90
    assert b.operated_days == 20
    assert b.share == 0.95


def test_rounding_up_and_never_negative() -> None:
    assert buffer([(90, 89)], 45, 90, 0.95, 5).needed_layover_min == 50  # 46 -> 50
    assert buffer([(90, 400)], 45, 90, 0.95, 5).needed_layover_min == 0  # -265 -> 0


def test_uses_each_days_scheduled_layover() -> None:
    # a schedule change: 60 minutes on one day, 120 on the other, both with zero delays
    b = buffer([(60, 60), (120, 120)], 45, 90, 0.6, 5)
    assert b.needed_layover_min == 45


def test_without_operated_days() -> None:
    # cancelled and diverted days are excluded before the call; none left
    b = buffer([], 45, 90, 0.95, 5)
    assert b.needed_layover_min is None
    assert b.operated_days == 0


@settings(max_examples=300, deadline=None)
@given(
    needed=st.lists(st.integers(-200, 400), min_size=1, max_size=400),
    share=st.sampled_from([0.6, 0.8, 0.9, 0.95, 0.99]),
)
def test_buffer_covers_at_least_the_share(needed: list[int], share: float) -> None:
    """The recommended layover would have been enough on at least ``share`` of the days."""
    b = buffer([(0, -n) for n in needed], 0, 90, share, 5)  # needed layover = n
    assert b.needed_layover_min is not None
    covered = sum(n <= b.needed_layover_min for n in needed)
    assert covered >= share * len(needed) - 1e-9


def test_thirty_days_cover_ninety_five_percent() -> None:
    # the review's case: needed 50, 55, ..., 195 -> 29 of 30 days need at most 190
    b = buffer([(0, -n) for n in range(50, 200, 5)], 0, 90, 0.95, 5)
    assert b.needed_layover_min == 190
