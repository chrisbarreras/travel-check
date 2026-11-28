"""Published showcase shapes (specs/002 data-model.md, contracts/outputs.md)."""

from __future__ import annotations

import datetime as dt
from typing import Any

import pytest
from pydantic import ValidationError

from flight_pipeline.showcase.models import (
    NOT_COVERED_KINDS,
    Alternative,
    ConnectingOption,
    Coverage,
    DailySeries,
    FailureBreakdown,
    MonthRate,
    Rate,
    Schedule,
    ShowcaseIndex,
)

CTX = {"min_sample": 30, "faster_margin": 0.02, "faster_min_saving_min": 15}


def rate(**kw: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "status": "ok",
        "rate": 0.9,
        "paired_days": 300,
        "count_feasible": 270,
        "definition": "connection_feasibility",
    }
    base.update(kw)
    return base


# --- Rate ---------------------------------------------------------------------------------


def test_rate_ok() -> None:
    assert Rate.model_validate(rate(), context=CTX).rate == 0.9


def test_insufficient_data_has_no_rate() -> None:
    r = Rate.model_validate(
        rate(status="insufficient_data", rate=None, paired_days=12, count_feasible=10),
        context=CTX,
    )
    assert r.rate is None
    with pytest.raises(ValidationError, match="insufficient"):
        Rate.model_validate(rate(status="insufficient_data", paired_days=12), context=CTX)


def test_ok_rate_needs_a_number_and_the_minimum_sample() -> None:
    with pytest.raises(ValidationError, match="rate"):
        Rate.model_validate(rate(rate=None), context=CTX)
    with pytest.raises(ValidationError, match="minimum"):
        Rate.model_validate(rate(paired_days=20, count_feasible=18), context=CTX)


def test_rate_matches_counts() -> None:
    with pytest.raises(ValidationError, match="count"):
        Rate.model_validate(rate(rate=0.5), context=CTX)


# --- Alternatives and options ------------------------------------------------------------


def alt(**kw: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "itinerary_id": "LGA-ATL-MCO:DL1200+DL1500",
        "minutes_saved": 60,
        "rate_this": rate(rate=0.95, paired_days=100, count_feasible=95),
        "rate_other": rate(rate=0.97, paired_days=100, count_feasible=97),
        "ci_low": -0.007,
        "ci_high": 0.049,
        "shared_days": 250,
    }
    base.update(kw)
    return base


def test_alternative_within_equivalence_bound() -> None:
    assert Alternative.model_validate(alt(), context=CTX).minutes_saved == 60


@pytest.mark.parametrize(
    ("kw", "message"),
    [
        ({"ci_low": -0.03}, "margin"),
        ({"minutes_saved": 10}, "saving"),
        ({"ci_low": 0.06, "ci_high": 0.05}, "ci_low"),
    ],
)
def test_alternative_rules(kw: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        Alternative.model_validate(alt(**kw), context=CTX)


def test_better_connecting_option_needs_an_interval_above_zero() -> None:
    base: dict[str, Any] = {
        "itinerary_id": "LGA-ATL-MCO:DL1259+DL1500",
        "outbound_dep_local_min": 900,
        "rate": rate(),
        "better": True,
        "ci_low": 0.15,
        "ci_high": 0.26,
    }
    assert ConnectingOption.model_validate(base, context=CTX).better
    with pytest.raises(ValidationError, match="better"):
        ConnectingOption.model_validate({**base, "ci_low": -0.01}, context=CTX)


# --- Daily series, months, failures ------------------------------------------------------


def test_daily_series_codes_and_nulls() -> None:
    d = DailySeries.model_validate(
        {"day_offset": [0, 1, 3, 4], "slack_min": [95, 40, None, None], "outcome": "FTCD"}
    )
    assert d.outcome == "FTCD"


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"day_offset": [0, 1], "slack_min": [5], "outcome": "FF"}, "length"),
        ({"day_offset": [1, 1], "slack_min": [5, 6], "outcome": "FF"}, "increasing"),
        ({"day_offset": [0], "slack_min": [None], "outcome": "F"}, "slack"),
        ({"day_offset": [0], "slack_min": [30], "outcome": "C"}, "slack"),
        ({"day_offset": [0], "slack_min": [30], "outcome": "X"}, "outcome"),
    ],
)
def test_daily_series_rules(data: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        DailySeries.model_validate(data)


def test_month_status_rules() -> None:
    ok = {"month": "2024-07", "status": "ok", "rate": 0.8, "paired_days": 25, "note_ids": []}
    assert MonthRate.model_validate(ok).rate == 0.8
    for bad, message in (
        ({**ok, "status": "insufficient_data"}, "rate"),
        ({**ok, "status": "no_flights", "rate": None}, "no_flights"),
        ({**ok, "status": "busy"}, "status"),
        ({**ok, "month": "2024-13"}, "month"),
    ):
        with pytest.raises(ValidationError, match=message):
            MonthRate.model_validate(bad)


def test_failure_breakdown_dominant() -> None:
    f = FailureBreakdown.model_validate(
        {"too_little_time": 70, "cancelled": 7, "diverted": 3, "dominant": "too_little_time"}
    )
    assert f.dominant == "too_little_time"
    with pytest.raises(ValidationError, match="dominant"):
        FailureBreakdown.model_validate(
            {"too_little_time": 1, "cancelled": 7, "diverted": 0, "dominant": "too_little_time"}
        )
    none = {"too_little_time": 0, "cancelled": 0, "diverted": 0, "dominant": "none"}
    assert FailureBreakdown.model_validate(none).dominant == "none"


# --- Index, coverage, attribution --------------------------------------------------------

PERIOD: dict[str, Any] = {
    "start": dt.date(2024, 7, 1),
    "end": dt.date(2025, 6, 30),
    "db1b_quarters": ["2024-3", "2024-4", "2025-1", "2025-2"],
}


def coverage(**kw: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "routes": ["LGA-MCO"],
        "hubs": ["ATL"],
        "airlines": [{"airline": "DL", "itineraries": 30, "sold_passengers": 1000}],
        "period": PERIOD,
        "not_covered": [{"kind": k, "text": f"{k} text"} for k in NOT_COVERED_KINDS],
    }
    base.update(kw)
    return base


def test_coverage_names_every_kind_not_covered() -> None:
    assert Coverage.model_validate(coverage())
    with pytest.raises(ValidationError, match="not_covered"):
        Coverage.model_validate(coverage(not_covered=[{"kind": "international", "text": "x"}]))
    assert set(NOT_COVERED_KINDS) == {
        "international",
        "two_or_more_stops",
        "separate_tickets",
        "non_reporting_airline",
        "outside_period",
        "not_in_showcase",
    }


def index(**kw: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "schema_version": "1.0.0",
        "period": PERIOD,
        "assumptions": {
            "min_connection_default_min": 30,
            "min_connection_partner_min": 45,
            "boarding_cutoff_min": 15,
            "recurrence_threshold": 0.6,
            "min_sample_days": 30,
            "monthly_min_sample": 20,
            "buffer_share": 0.95,
            "faster_margin": 0.02,
            "faster_min_saving_min": 15,
        },
        "coverage": coverage(),
        "balance": {
            "caps": {"route": 0.333333, "airline": 0.5, "hub": 0.5, "cross_hub_min": 0.5},
            "airline_shares": {"DL": 0.5},
            "hub_shares": {"ATL": 0.5},
            "cross_hub_share": 0.6,
            "shortfalls": [],
        },
        "routes": [],
        "airports": [],
        "landing": {"route_id": "LGA-MCO", "comparison_id": "c1", "reason": "strongest"},
        "definitions": [
            {"key": "connection_feasibility", "text": "Share of days", "methodology_anchor": "#x"}
        ],
        "attribution": [
            {"source": s, "text": f"{s} data", "licence": "public", "url": "https://example.org"}
            for s in ("BTS", "airportsdata", "tzdata")
        ],
        "manifest": {
            "code_version": "0.2.0",
            "config_sha256": "0" * 64,
            "manifest": "manifest.json",
        },
    }
    base.update(kw)
    return base


def test_index_valid() -> None:
    assert ShowcaseIndex.model_validate(index()).schema_version == "1.0.0"


@pytest.mark.parametrize(
    ("kw", "message"),
    [
        ({"schema_version": "1.0"}, "schema_version"),
        ({"attribution": []}, "attribution"),
        ({"definitions": []}, "connection_feasibility"),
    ],
)
def test_index_rules(kw: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        ShowcaseIndex.model_validate(index(**kw))


# --- Explorer additions (specs/004-explorer-core FR-001, FR-002) ---------------------------


def airport(code: str, **kw: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "code": code,
        "name": f"{code} airport",
        "city": f"{code} city",
        "lat": 40.0,
        "lon": -90.0,
    }
    base.update(kw)
    return base


def route(origin: str, dest: str) -> dict[str, Any]:
    return {
        "route_id": f"{origin}-{dest}",
        "origin": origin,
        "dest": dest,
        "regional_origin": False,
        "itinerary_count": 1,
        "comparison_count": 1,
        "share_of_showcase": 1.0,
        "nonstop_median_min": None,
        "file": f"routes/{origin}-{dest}.json",
    }


def test_index_lists_airports_sorted_by_code() -> None:
    model = ShowcaseIndex.model_validate(
        index(routes=[route("LIT", "LGA")], airports=[airport("LGA"), airport("LIT")])
    )
    assert [a.code for a in model.airports] == ["LGA", "LIT"]


@pytest.mark.parametrize(
    ("airports", "message"),
    [
        ([airport("LIT")], "LGA"),
        ([airport("LIT"), airport("LGA"), airport("LGA")], "once"),
        ([airport("LIT"), airport("LGA", lat=91.0)], "lat"),
        ([airport("LIT"), airport("LGA", lon=-181.0)], "lon"),
        ([airport("LIT"), airport("lga")], "code"),
        ([airport("LIT"), airport("LGA", name="")], "name"),
    ],
)
def test_index_airport_rules(airports: list[dict[str, Any]], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        ShowcaseIndex.model_validate(index(routes=[route("LIT", "LGA")], airports=airports))


def schedule(**kw: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "dep_local_min": 758,
        "arr_local_min": 1153,
        "layover_min": 99,
        "travel_min": 327,
        "nonstop_median_min": 175,
        "nonstop_ratio": 1.9,
        "hub_arr_local_min": 913,
        "hub_dep_local_min": 1012,
        "inbound_min": 95,
        "outbound_min": 133,
    }
    base.update(kw)
    return base


def test_schedule_carries_hub_times_and_flight_durations() -> None:
    model = Schedule.model_validate(schedule())
    assert (model.hub_arr_local_min, model.hub_dep_local_min) == (913, 1012)
    assert (model.inbound_min, model.outbound_min) == (95, 133)


@pytest.mark.parametrize(
    ("kw", "message"),
    [
        ({"hub_arr_local_min": 1440}, "hub_arr_local_min"),
        ({"hub_dep_local_min": -1}, "hub_dep_local_min"),
        ({"inbound_min": 0}, "inbound_min"),
        ({"outbound_min": 0}, "outbound_min"),
        ({"inbound_min": 96}, "travel"),
        ({"hub_dep_local_min": 1020}, "layover"),
    ],
)
def test_schedule_addition_rules(kw: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        Schedule.model_validate(schedule(**kw))


def test_hub_departure_wraps_past_midnight() -> None:
    model = Schedule.model_validate(
        schedule(hub_arr_local_min=1400, hub_dep_local_min=(1400 + 99) % 1440)
    )
    assert model.hub_dep_local_min == 59
