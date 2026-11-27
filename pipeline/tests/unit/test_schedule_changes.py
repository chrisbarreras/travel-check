"""Schedule changes (research R13, FR-023) and find parameters (research R14, FR-024)."""

from __future__ import annotations

import datetime as dt

from flight_pipeline.insights.schedule import find_params, schedule_changes, schedule_warnings

START = dt.date(2024, 7, 1)


def series(*runs: tuple[int, int]) -> list[tuple[dt.date, int]]:
    """Consecutive scheduled days: (minute, number of days) runs."""
    out: list[tuple[dt.date, int]] = []
    for minute, n in runs:
        for _ in range(n):
            out.append((START + dt.timedelta(days=len(out)), minute))
    return out


def changes(days, joins=()):  # type: ignore[no-untyped-def]
    return schedule_changes(days, list(joins), "inbound", min_shift_min=10, min_days=7)


def test_lasting_change_is_reported_with_date_and_times() -> None:
    [c] = changes(series((480, 30), (495, 30)))
    assert c.date == START + dt.timedelta(days=30)
    assert (c.leg, c.from_local_min, c.to_local_min) == ("inbound", 480, 495)


def test_short_or_small_shifts_are_not_changes() -> None:
    assert changes(series((480, 30), (495, 6), (480, 30))) == []  # 6 days only
    assert changes(series((480, 30), (489, 30))) == []  # 9 minutes only
    assert changes(series((480, 30), (490, 7))) != []  # exactly 10 minutes for 7 days


def test_outlier_days_do_not_move_the_reference() -> None:
    days = series((480, 20), (530, 1), (480, 20), (500, 10))
    [c] = changes(days)
    assert (c.from_local_min, c.to_local_min) == (480, 500)


def test_successive_changes_and_across_midnight() -> None:
    days = series((1435, 10), (5, 10), (30, 10))
    got = [(c.from_local_min, c.to_local_min) for c in changes(days)]
    assert got == [(1435, 5), (5, 30)]


def test_slot_joins_are_changes_whatever_their_length() -> None:
    join_date = START + dt.timedelta(days=12)
    [c] = changes(series((480, 30)), joins=[(join_date, 480, 470)])
    assert (c.date, c.from_local_min, c.to_local_min) == (join_date, 480, 470)


def test_warnings_merge_both_legs_by_date() -> None:
    inbound = changes(series((480, 30), (495, 30)))
    outbound = schedule_changes(
        series((700, 10), (730, 50)), [], "outbound", min_shift_min=10, min_days=7
    )
    w = schedule_warnings(0.92, 300, inbound, outbound)
    assert (w.connecting_days, w.eligible_days) == (276, 300)
    assert w.connect_share == 0.92
    assert [(c.leg, c.date) for c in w.changes] == [
        ("outbound", START + dt.timedelta(days=10)),
        ("inbound", START + dt.timedelta(days=30)),
    ]
    assert schedule_warnings(1.0, 300, [], []).changes == []


def test_find_uses_the_most_frequent_flight_number_per_leg() -> None:
    f = find_params(
        "CMH",
        "SAN",
        ["WN", "WN"],
        [[("WN2001", 0.5), ("WN1001", 0.5)], [("WN3000", 0.9), ("WN3100", 0.1)]],
    )
    assert (f.origin, f.dest, f.airlines) == ("CMH", "SAN", ["WN"])
    assert [(leg.flight_number, leg.share_of_days) for leg in f.legs] == [
        ("WN1001", 0.5),  # tie: the smaller number
        ("WN3000", 0.9),
    ]
