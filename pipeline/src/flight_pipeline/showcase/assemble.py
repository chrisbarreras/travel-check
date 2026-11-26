"""Assemble the published shapes from the derived tables (specs/002 data-model.md).

The curated routes and comparisons come from ``curate``; each itinerary carries its default
result, schedule, per-day series and sold routing, and the traveler insights from the
``insights`` stage.
"""

from __future__ import annotations

import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path

import duckdb

from flight_pipeline.config import Config, DisruptionNote
from flight_pipeline.coverage import airline_coverage
from flight_pipeline.insights.build import rate_of
from flight_pipeline.models import (
    ComparablePair,
    CuratedComparisonRow,
    CuratedRouteRow,
    DailyOutcome,
    Itinerary,
    ItineraryResult,
    NonstopMedian,
)
from flight_pipeline.nonstop import nonstop_ratio
from flight_pipeline.showcase.models import (
    Assumptions,
    DataPeriod,
    ExcludedDays,
    ItineraryInsights,
    LandingRef,
    ManifestRef,
    RouteFile,
    RouteSummary,
    Schedule,
    ShowcaseComparison,
    ShowcaseIndex,
    ShowcaseItinerary,
    SoldRouting,
)
from flight_pipeline.showcase.publish import (
    ATTRIBUTION,
    SCHEMA_VERSION,
    coverage,
    definitions,
    notes_for_route,
)
from flight_pipeline.showcase.slider import daily_series


def _no_counts() -> dict[str, int]:
    return {}


@dataclass(frozen=True)
class Inputs:
    """Everything the assembly reads, already loaded."""

    routes: Sequence[CuratedRouteRow]
    comparisons: Sequence[CuratedComparisonRow]
    landing_comparison_id: str | None
    landing_reason: str
    itineraries: Mapping[str, Itinerary]
    results: Mapping[str, ItineraryResult]  # default scenario
    pairs: Mapping[tuple[str, str], ComparablePair]
    missing_settings: Mapping[tuple[str, str], str]
    nonstop: Mapping[tuple[str, str], NonstopMedian]
    arrival_local_min: Mapping[str, int]  # by outbound slot
    insights: Mapping[str, ItineraryInsights]
    hubs: Sequence[str]
    sold_same_airline: Mapping[str, int]
    tight: frozenset[str]
    daily: Mapping[str, Sequence[DailyOutcome]]  # default scenario, paired days
    notes: Sequence[DisruptionNote]
    # Itineraries per inbound marketing airline in the whole analysis (coverage notes)
    analysis_itineraries: Mapping[str, int] = field(default_factory=_no_counts)


def data_period(cfg: Config) -> DataPeriod:
    return DataPeriod(
        start=cfg.period.dates()[0],
        end=cfg.period.dates()[1],
        db1b_quarters=[f"{y}-{q}" for y, q in cfg.period.quarters()],
    )


def assumptions(cfg: Config) -> Assumptions:
    return Assumptions(
        min_connection_default_min=cfg.itineraries.min_connection_default_min,
        min_connection_partner_min=cfg.itineraries.min_connection_partner_min,
        boarding_cutoff_min=cfg.feasibility.boarding_cutoff_min,
        recurrence_threshold=cfg.itineraries.recurrence_threshold,
        min_sample_days=cfg.feasibility.min_sample_days,
        monthly_min_sample=cfg.insights.monthly_min_sample,
        buffer_share=cfg.insights.buffer_share,
        faster_margin=cfg.insights.faster_margin,
        faster_min_saving_min=cfg.insights.faster_min_saving_min,
    )


def showcase_itinerary(it: Itinerary, inputs: Inputs, cfg: Config) -> ShowcaseItinerary:
    r = inputs.results[it.itinerary_id]
    ins = inputs.insights[it.itinerary_id]
    ns = inputs.nonstop.get((it.origin, it.dest))
    ns_min = ns.nonstop_median_min if ns else None
    return ShowcaseItinerary(
        itinerary_id=it.itinerary_id,
        hub=it.hub,
        airline=it.airline_in,
        airline_out=it.airline_out,
        partner_connection=it.partner_connection,
        min_connection_min=cfg.itineraries.min_connection_for(
            it.hub, partner=it.partner_connection
        ),
        schedule=Schedule(
            dep_local_min=it.median_dep_local_min,
            arr_local_min=inputs.arrival_local_min.get(it.outbound_slot, 0),
            layover_min=it.median_layover_min,
            travel_min=it.median_travel_min,
            nonstop_median_min=ns_min,
            nonstop_ratio=nonstop_ratio(it.median_travel_min, ns_min),
        ),
        result=rate_of(r),
        failures=ins.failures,
        daily=daily_series(inputs.daily.get(it.itinerary_id, []), cfg.period.dates()[0]),
        excluded_days=ExcludedDays(
            not_connecting=r.excluded_not_connecting,
            quality=r.excluded_quality,
            end_of_period=r.excluded_end_of_period,
        ),
        monthly=ins.monthly,
        buffer=ins.buffer,
        faster_alternatives=ins.faster_alternatives,
        connecting_options=ins.connecting_options,
        schedule_warnings=ins.schedule_warnings,
        find=ins.find,
        tight_layover=it.itinerary_id in inputs.tight,
        sold=SoldRouting(passengers=it.sold_passengers, routing_itineraries=it.routing_itineraries),
    )


def _comparison(c: CuratedComparisonRow, inputs: Inputs) -> ShowcaseComparison:
    p = inputs.pairs[(c.itinerary_a, c.itinerary_b)]
    ra = inputs.results[c.itinerary_a].feasibility_rate or 0.0
    rb = inputs.results[c.itinerary_b].feasibility_rate or 0.0
    # itinerary_a is the higher rate; the interval is oriented the same way
    flip = rb > ra
    low, high = p.ci_low or 0.0, p.ci_high or 0.0
    return ShowcaseComparison(
        comparison_id=c.comparison_id,
        itinerary_a=c.itinerary_b if flip else c.itinerary_a,
        itinerary_b=c.itinerary_a if flip else c.itinerary_b,
        difference=c.difference,
        ci_low=-high if flip else low,
        ci_high=-low if flip else high,
        shared_days=p.shared_days,
        settings_compared=p.settings_compared,
        missing_settings_note=inputs.missing_settings.get((c.itinerary_a, c.itinerary_b), ""),
        cross_hub=c.cross_hub,
        landing=c.landing,
    )


def route_itineraries(
    candidates: Sequence[Itinerary], compared: set[str], limit: int
) -> list[Itinerary]:
    """The route's itineraries in its file: every compared itinerary, then the others by sold
    passengers (then id) up to ``limit`` (the compared set alone may exceed it). Sorted by
    id."""
    must = [i for i in candidates if i.itinerary_id in compared]
    rest = sorted(
        (i for i in candidates if i.itinerary_id not in compared),
        key=lambda i: (-i.sold_passengers, i.itinerary_id),
    )
    chosen = must + rest[: max(0, limit - len(must))]
    return sorted(chosen, key=lambda i: i.itinerary_id)


def route_files(inputs: Inputs, cfg: Config) -> list[RouteFile]:
    period = data_period(cfg)
    out: list[RouteFile] = []
    for route in inputs.routes:
        comps = [c for c in inputs.comparisons if c.route_id == route.route_id]
        its = route_itineraries(
            [i for i in inputs.itineraries.values() if f"{i.origin}-{i.dest}" == route.route_id],
            {x for c in comps for x in (c.itinerary_a, c.itinerary_b)},
            cfg.showcase.itineraries_per_route_max,
        )
        out.append(
            RouteFile(
                route_id=route.route_id,
                period=period,
                itineraries=[showcase_itinerary(i, inputs, cfg) for i in its],
                comparisons=[_comparison(c, inputs) for c in comps],
                disruption_notes=notes_for_route(
                    inputs.notes,
                    route.origin,
                    {i.hub for i in its},
                    route.dest,
                    {a for i in its for a in (i.airline_in, i.airline_out)},
                ),
            )
        )
    return out


def code_identity(repo_root: Path) -> tuple[str, str]:
    """The package version and the git commit (``unknown`` outside git)."""
    version = metadata.version("flight-pipeline")
    try:
        done = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        return version, done.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return version, "unknown"


def index_of(
    routes: Sequence[RouteFile], inputs: Inputs, cfg: Config, config_sha256: str
) -> ShowcaseIndex:
    period = data_period(cfg)
    if inputs.landing_comparison_id is None:
        raise ValueError("no landing example: curation found none that meets the rule")
    landing_route = next(
        c.route_id for c in inputs.comparisons if c.comparison_id == inputs.landing_comparison_id
    )
    by_route = {r.route_id: r for r in routes}
    shown = [i for r in routes for i in r.itineraries]
    version, _ = code_identity(cfg.repo_root)
    summaries = [
        RouteSummary(
            route_id=r.route_id,
            origin=r.origin,
            dest=r.dest,
            regional_origin=r.regional_origin,
            itinerary_count=len(by_route[r.route_id].itineraries),
            comparison_count=r.comparison_count,
            share_of_showcase=r.share_of_showcase,
            nonstop_median_min=(
                inputs.nonstop[(r.origin, r.dest)].nonstop_median_min
                if (r.origin, r.dest) in inputs.nonstop
                else None
            ),
            file=f"routes/{r.route_id}.json",
        )
        for r in inputs.routes
    ]
    return ShowcaseIndex(
        schema_version=SCHEMA_VERSION,
        period=period,
        assumptions=assumptions(cfg),
        coverage=coverage(
            [r.route_id for r in inputs.routes],
            sorted({i.hub for i in shown}),
            airline_coverage(
                [i.airline for i in shown],
                inputs.sold_same_airline,
                cfg.hubs.major_networks,
                inputs.analysis_itineraries,
            ),
            period,
        ),
        routes=summaries,
        landing=LandingRef(
            route_id=landing_route,
            comparison_id=inputs.landing_comparison_id,
            reason=inputs.landing_reason,
        ),
        definitions=definitions(),
        attribution=list(ATTRIBUTION),
        manifest=ManifestRef(
            code_version=version,
            config_sha256=config_sha256,
            manifest="manifest.json",
        ),
    )


# --- Loading -----------------------------------------------------------------------------


def arrival_minutes(
    con: duckdb.DuckDBPyConnection, slots_days: str, flights: str
) -> dict[str, int]:
    """Median scheduled local arrival minute over each slot's days."""
    rows = con.execute(
        f"""
        SELECT d.slot_id, quantile_disc(f.sched_arr_local_min, 0.5)
        FROM {slots_days} d JOIN {flights} f
          ON f.marketing_airline = d.marketing_airline AND f.flight_number = d.flight_number
         AND f.origin = d.origin AND f.service_date = d.service_date
        WHERE f.quality_flag <> 'duplicate'
        GROUP BY d.slot_id
        """
    ).fetchall()
    return {str(s): int(m) for s, m in rows}


def sold_same_airline(
    con: duckdb.DuckDBPyConnection, sold: str, hubs: Sequence[str]
) -> dict[str, int]:
    """Sampled DB1B passengers on sold same-airline routings through the selected hubs."""
    if not hubs:
        return {}
    listed = ", ".join(f"'{h}'" for h in hubs)
    rows = con.execute(
        f"SELECT airline_in, sum(passengers) FROM {sold} "
        f"WHERE airline_in = airline_out AND hub IN ({listed}) GROUP BY airline_in"
    ).fetchall()
    return {str(a): int(n) for a, n in rows}
