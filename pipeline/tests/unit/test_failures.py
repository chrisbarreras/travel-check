"""Failure breakdown (FR-021)."""

from __future__ import annotations

import pytest

from flight_pipeline.insights.monthly import failure_breakdown


@pytest.mark.parametrize(
    ("counts", "dominant"),
    [
        ((5, 2, 1), "too_little_time"),
        ((1, 4, 0), "cancelled"),
        ((0, 1, 3), "diverted"),
        ((0, 0, 0), "none"),
        ((2, 2, 1), "too_little_time"),  # ties in the order too little time, cancelled, diverted
        ((0, 3, 3), "cancelled"),
    ],
)
def test_dominant_type(counts: tuple[int, int, int], dominant: str) -> None:
    b = failure_breakdown(*counts)
    assert (b.too_little_time, b.cancelled, b.diverted) == counts
    assert b.dominant == dominant
