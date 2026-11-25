"""Showcase examples and the go criterion (User Story 5 scenarios 1-3; FR-029, FR-030)."""

from typing import Any

import pytest

from flight_pipeline.compare import go_criteria, is_showcase, order_pair


def case(**kw: Any) -> dict[str, Any]:
    base: dict[str, Any] = dict(
        rate_a=0.85,
        rate_b=0.70,
        sufficient_a=True,
        sufficient_b=True,
        ci_low=0.05,
        ci_high=0.25,
        assumption_sensitive=False,
        gap=0.10,
        shared_days=200,
        min_shared_days=30,
    )
    base.update(kw)
    return base


def test_all_conditions_met_is_showcase() -> None:
    assert is_showcase(**case())


@pytest.mark.parametrize(
    ("change", "why"),
    [
        ({"sufficient_b": False, "rate_b": None}, "insufficient data"),
        ({"rate_b": 0.76}, "gap 9 points < 10"),
        ({"ci_low": -0.01}, "interval includes zero"),
        ({"assumption_sensitive": True}, "assumption-sensitive"),
        ({"ci_low": None, "ci_high": None}, "no interval"),
        ({"shared_days": 29}, "fewer than 30 shared dates"),
        ({"shared_days": 0}, "never flew on the same dates"),
    ],
)
def test_each_condition_is_required(change: dict[str, Any], why: str) -> None:
    assert not is_showcase(**case(**change)), why


def test_exactly_ten_points_qualifies() -> None:
    assert is_showcase(**case(rate_a=0.80, rate_b=0.70))


def test_twelve_point_gap_with_interval_including_zero_is_not_showcase() -> None:
    # User Story 5 scenario 3
    assert not is_showcase(**case(rate_a=0.82, rate_b=0.70, ci_low=-0.02, ci_high=0.26))


def test_pair_order_higher_rate_first_ties_and_nulls_by_id() -> None:
    assert order_pair("x", "y", 0.6, 0.8) == ("y", "x")
    assert order_pair("x", "y", 0.8, 0.6) == ("x", "y")
    assert order_pair("y", "x", 0.7, 0.7) == ("x", "y")
    assert order_pair("y", "x", None, 0.7) == ("x", "y")


def test_go_criteria() -> None:
    # (hubs of itinerary a, hubs of itinerary b) per showcase example
    assert go_criteria([("ORD", "ORD"), ("ORD", "DFW"), ("ATL", "ATL")], 3, 2) == (True, True)
    assert go_criteria([("ORD", "ORD"), ("ORD", "ORD"), ("ORD", "ORD")], 3, 2) == (True, False)
    assert go_criteria([("ORD", "DFW"), ("ATL", "ATL")], 3, 2) == (False, True)
    assert go_criteria([], 3, 2) == (False, False)
    # an example counts toward the hubs of both its itineraries
    assert go_criteria([("ORD", "DFW"), ("ORD", "ORD"), ("ORD", "ORD")], 3, 2) == (True, True)
    assert go_criteria([("DFW", "ORD"), ("ORD", "ORD"), ("ORD", "ORD")], 3, 2) == (True, True)


def test_shared_days_counts_dates_both_have_outcomes() -> None:
    import datetime as dt

    from flight_pipeline.compare import shared_days

    d = [dt.date(2026, 1, i) for i in range(1, 8)]
    assert (
        shared_days({d[0]: True, d[1]: False, d[2]: True}, {d[1]: True, d[2]: True, d[6]: True})
        == 2
    )
    assert shared_days({d[0]: True}, {d[5]: True}) == 0
