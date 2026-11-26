"""Monthly view and disruption notes (research R11, R12, FR-022)."""

from __future__ import annotations

import datetime as dt

from flight_pipeline.config import DisruptionNote
from flight_pipeline.insights.monthly import monthly_view, notes_for_month

MONTHS = ["2024-07", "2024-08", "2024-09"]


def note(nid: str, start: str, end: str, *, airlines=(), airports=()) -> DisruptionNote:  # type: ignore[no-untyped-def]
    return DisruptionNote(
        note_id=nid,
        start=dt.date.fromisoformat(start),
        end=dt.date.fromisoformat(end),
        airlines=list(airlines),
        airports=list(airports),
        text="An event.",
        source_url="https://example.gov/event",
    )


def view(paired, flown=(), notes=(), min_sample=20):  # type: ignore[no-untyped-def]
    return monthly_view(
        MONTHS, paired, flown, min_sample, list(notes), ["DL"], ["CMH", "ATL", "SAN"]
    )


def test_monthly_minimum_sample() -> None:
    rows = view({"2024-07": (20, 15), "2024-08": (19, 19)}, flown=["2024-07", "2024-08"])
    assert [(r.month, r.status, r.rate, r.paired_days) for r in rows] == [
        ("2024-07", "ok", 0.75, 20),
        ("2024-08", "insufficient_data", None, 19),
        ("2024-09", "no_flights", None, 0),
    ]


def test_scheduled_but_never_paired_is_insufficient_not_no_flights() -> None:
    rows = view({}, flown=["2024-09"])
    assert rows[2].status == "insufficient_data"
    assert rows[2].paired_days == 0


def test_notes_attach_by_date_overlap_and_airline_or_airport() -> None:
    notes = [
        note("storm", "2024-08-30", "2024-09-02", airports=["ATL"]),  # overlaps Aug and Sep
        note("outage", "2024-07-19", "2024-07-21", airlines=["DL"]),
        note("elsewhere", "2024-07-01", "2024-07-31", airports=["ORD"], airlines=["UA"]),
    ]
    rows = view({"2024-07": (25, 20)}, flown=MONTHS, notes=notes)
    assert [r.note_ids for r in rows] == [["outage"], ["storm"], ["storm"]]


def test_notes_never_change_a_value() -> None:
    paired = {"2024-07": (25, 20)}
    with_notes = view(paired, MONTHS, [note("outage", "2024-07-19", "2024-07-21", airlines=["DL"])])
    without = view(paired, MONTHS, [])
    assert [(r.status, r.rate, r.paired_days) for r in with_notes] == [
        (r.status, r.rate, r.paired_days) for r in without
    ]


def test_note_on_month_boundaries() -> None:
    n = note("x", "2024-07-31", "2024-07-31", airports=["SAN"])
    assert notes_for_month([n], "2024-07", [], ["SAN"]) == ["x"]
    assert notes_for_month([n], "2024-08", [], ["SAN"]) == []
