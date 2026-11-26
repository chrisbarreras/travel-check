"""Small valid published shapes for unit tests (specs/002 data-model.md)."""

from __future__ import annotations

import datetime as dt
from typing import Any

from flight_pipeline.showcase.models import (
    Assumptions,
    Buffer,
    DailySeries,
    DataPeriod,
    ExcludedDays,
    FailureBreakdown,
    FindLeg,
    FindParams,
    LandingRef,
    ManifestRef,
    Rate,
    RouteFile,
    RouteSummary,
    Schedule,
    ScheduleWarnings,
    ShowcaseComparison,
    ShowcaseIndex,
    ShowcaseItinerary,
    SoldRouting,
)
from flight_pipeline.showcase.publish import ATTRIBUTION, coverage, definitions

PERIOD = DataPeriod(
    start=dt.date(2024, 7, 1),
    end=dt.date(2025, 6, 30),
    db1b_quarters=["2024-3", "2024-4", "2025-1", "2025-2"],
)


def rate(paired: int = 40, feasible: int = 36) -> Rate:
    return Rate(
        status="ok",
        rate=feasible / paired,
        paired_days=paired,
        count_feasible=feasible,
        definition="connection_feasibility",
    )


def itinerary(iid: str, hub: str = "ORD", *, paired: int = 40, feasible: int = 36, **kw: Any):
    base: dict[str, Any] = {
        "itinerary_id": iid,
        "hub": hub,
        "airline": "UA",
        "airline_out": "UA",
        "partner_connection": False,
        "min_connection_min": 30,
        "schedule": Schedule(
            dep_local_min=480,
            arr_local_min=840,
            layover_min=90,
            travel_min=400,
            nonstop_median_min=None,
            nonstop_ratio=None,
        ),
        "result": rate(paired, feasible),
        "failures": FailureBreakdown(
            too_little_time=paired - feasible,
            cancelled=0,
            diverted=0,
            dominant="too_little_time" if paired > feasible else "none",
        ),
        "daily": DailySeries(
            day_offset=list(range(paired)),
            slack_min=list[int | None]([60] * feasible + [10] * (paired - feasible)),
            outcome="F" * feasible + "T" * (paired - feasible),
        ),
        "excluded_days": ExcludedDays(not_connecting=0, quality=0, end_of_period=0),
        "monthly": [],
        "buffer": Buffer(
            share=0.95, needed_layover_min=None, actual_layover_min=90, operated_days=0
        ),
        "faster_alternatives": [],
        "connecting_options": [],
        "schedule_warnings": ScheduleWarnings(connect_share=1.0, changes=[]),
        "find": FindParams(
            origin="CMH",
            dest="SAN",
            airlines=["UA"],
            legs=[FindLeg(flight_number="UA1", share_of_days=1.0)],
        ),
        "tight_layover": False,
        "sold": SoldRouting(passengers=40, routing_itineraries=1),
    }
    base.update(kw)
    return ShowcaseItinerary(**base)


def comparison(a: str, b: str, *, landing: bool = False, cross: bool = True) -> ShowcaseComparison:
    return ShowcaseComparison(
        comparison_id=f"{a}|{b}",
        itinerary_a=a,
        itinerary_b=b,
        difference=0.2,
        ci_low=0.1,
        ci_high=0.3,
        shared_days=40,
        settings_compared=9,
        missing_settings_note="",
        cross_hub=cross,
        landing=landing,
    )


A = "CMH-ORD-SAN:UA0800+UA1100"
B = "CMH-DEN-SAN:UA0805+UA1130"
C = "CMH-DFW-SAN:AA0810+AA1200"


def route_file(route_id: str = "CMH-SAN", **kw: Any) -> RouteFile:
    base: dict[str, Any] = {
        "route_id": route_id,
        "period": PERIOD,
        "itineraries": [
            itinerary(A, "ORD"),
            itinerary(B, "DEN", feasible=28),
            itinerary(C, "DFW", feasible=20),
        ],
        "comparisons": [comparison(A, B, landing=True), comparison(A, C)],
        "disruption_notes": [],
    }
    base.update(kw)
    return RouteFile(**base)


def assumptions() -> Assumptions:
    return Assumptions(
        min_connection_default_min=45,
        min_connection_partner_min=60,
        boarding_cutoff_min=15,
        recurrence_threshold=0.8,
        min_sample_days=30,
        monthly_min_sample=20,
        buffer_share=0.95,
        faster_margin=0.02,
        faster_min_saving_min=15,
    )


def index(routes: list[RouteFile] | None = None, **kw: Any) -> ShowcaseIndex:
    routes = routes or [route_file()]
    base: dict[str, Any] = {
        "schema_version": "1.0.0",
        "period": PERIOD,
        "assumptions": assumptions(),
        "coverage": coverage([r.route_id for r in routes], ["DEN", "DFW", "ORD"], [], PERIOD),
        "routes": [
            RouteSummary(
                route_id=r.route_id,
                origin=r.route_id[:3],
                dest=r.route_id[4:],
                regional_origin=True,
                itinerary_count=len(r.itineraries),
                comparison_count=len(r.comparisons),
                share_of_showcase=1.0 / len(routes),
                nonstop_median_min=None,
                file=f"routes/{r.route_id}.json",
            )
            for r in routes
        ],
        "landing": LandingRef(
            route_id=routes[0].route_id,
            comparison_id=routes[0].comparisons[0].comparison_id,
            reason="strongest cross-hub comparison",
        ),
        "definitions": definitions(),
        "attribution": list(ATTRIBUTION),
        "manifest": ManifestRef(
            code_version="0.2.0", config_sha256="0" * 64, manifest="manifest.json"
        ),
    }
    base.update(kw)
    return ShowcaseIndex(**base)


CONTEXT: dict[str, Any] = {"min_sample": 30, "faster_margin": 0.02, "faster_min_saving_min": 15}
