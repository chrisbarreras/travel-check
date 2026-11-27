"""Pipeline stages after acquisition (contracts/cli.md). Each stage reads only its declared
inputs from ``derived_dir`` and writes its outputs there (or to ``reports_dir``)."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import statistics
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, replace
from importlib import metadata
from pathlib import Path
from typing import Any

import duckdb
from pydantic import TypeAdapter

from flight_pipeline.compare import (
    BootstrapTask,
    comparable_candidates,
    feasibility_threshold,
    go_criteria,
    is_showcase,
    order_pair,
    paired_bootstraps,
    shared_days,
    tight_itineraries,
)
from flight_pipeline.config import Config, load_disruption_notes
from flight_pipeline.curation import CandidateComparison, RouteCandidate, curate
from flight_pipeline.hubs import (
    assign_roles,
    candidate_metrics,
    candidate_pool,
    count_eligible,
    select_hubs,
)
from flight_pipeline.insights.build import ItineraryData, SlotData, build_insights
from flight_pipeline.itineraries import build_itineraries
from flight_pipeline.models import (
    Airport,
    ComparablePair,
    CuratedComparisonRow,
    CuratedRouteRow,
    CurationMeta,
    DailyOutcome,
    Finding,
    HubCandidate,
    HubSelection,
    HubSelectionMeta,
    Itinerary,
    ItineraryDay,
    ItineraryResult,
    Manifest,
    NonstopMedian,
    OdExclusions,
    OdSelection,
    OdSelectionMeta,
    QualitySummary,
    ScenarioSummary,
    ScheduleSlot,
    SensitivityMeta,
    SensitivityScenario,
    SlotChange,
    SlotDay,
    SoldRoutingsSummary,
    validate_scenarios,
)
from flight_pipeline.nonstop import nonstop_medians
from flight_pipeline.od_selection import od_candidates, select_od_pairs, selection_shortfalls
from flight_pipeline.prepare.db1b import unmapped_airlines
from flight_pipeline.providers.timezones import AirportsDataTimezones
from flight_pipeline.report import (
    CI_METHOD,
    LIMITATIONS,
    airline_coverage,
    airline_section,
    breakdown_section,
    curation_section,
    describe_missing_settings,
    exclusions_section,
    finding_json,
    hub_of_id,
    hub_section,
    od_section,
    render_summary,
    results_section,
    routing_itineraries,
    sensitivity_section,
    showcase_breakdown,
    showcase_section,
)
from flight_pipeline.sensitivity import (
    evaluate_scenarios,
    missing_settings,
    reversal_flags,
    reversals_by_scenario,
    scenario_id,
    scenarios,
    settings_compared,
)
from flight_pipeline.showcase import assemble
from flight_pipeline.showcase.models import InsightsFile, ShowcaseManifest
from flight_pipeline.showcase.publish import render, validation_context, write_files
from flight_pipeline.slots import build_slots
from flight_pipeline.storage import (
    THREADS_ENV,
    models_to_table,
    read_models,
    read_table,
    write_table,
)


def derived(cfg: Config, name: str) -> Path:
    return cfg.path(cfg.paths.derived_dir) / name


def reports(cfg: Config, name: str) -> Path:
    return cfg.path(cfg.paths.reports_dir) / name


def write_json(path: Path, data: Any, model: Any = None) -> None:
    """Write ``data`` as stable JSON; with ``model`` (a Pydantic model class or a
    ``TypeAdapter``), validate it first so the file always matches its declared shape."""
    if model is not None:
        _validate(model, data)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def read_json(path: Path, model: Any = None) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"{path} not found; run the earlier pipeline stages first")
    data = json.loads(path.read_text(encoding="utf-8"))
    if model is not None:
        _validate(model, data)
    return data


def _validate(model: Any, data: Any) -> None:
    if isinstance(model, TypeAdapter):
        model.validate_python(data)  # pyright: ignore[reportUnknownMemberType]
    else:
        model.model_validate(data)


SCENARIO_SUMMARIES: TypeAdapter[list[ScenarioSummary]] = TypeAdapter(list[ScenarioSummary])


def load_flights(con: duckdb.DuckDBPyConnection, cfg: Config) -> None:
    read_table(con, derived(cfg, "flights.parquet"), "flights")
    read_table(con, derived(cfg, "sold_routings.parquet"), "sold_routings")


def load_slots(con: duckdb.DuckDBPyConnection, cfg: Config) -> None:
    for name in ("slots", "slots_days", "slots_changes"):
        read_table(con, derived(cfg, f"{name}.parquet"), name)


def stage_select_hubs(con: duckdb.DuckDBPyConnection, cfg: Config) -> str:
    load_flights(con, cfg)
    read_table(con, derived(cfg, "passengers.parquet"), "passengers")
    pool = candidate_pool(con, "flights", cfg.hubs.candidate_pool_size)
    metrics = candidate_metrics(con, "flights", "passengers", pool, cfg.hubs)
    build_slots(con, "flights", cfg.period.dates(), cfg.itineraries.slot_window_min, "slots")
    write_table(con, "slots", derived(cfg, "slots.parquet"), ScheduleSlot, ["slot_id"])
    write_table(
        con,
        "slots_days",
        derived(cfg, "slots_days.parquet"),
        SlotDay,
        ["slot_id", "service_date"],
    )
    write_table(
        con,
        "slots_changes",
        derived(cfg, "slots_changes.parquet"),
        SlotChange,
        ["slot_id", "change_date"],
    )
    build_itineraries(
        con,
        "slots",
        pool,
        cfg.itineraries,
        "pool_itineraries",
        flights="flights",
        sold="sold_routings",
        period=cfg.period.dates(),
        days=False,
    )
    eligible = count_eligible(con, "pool_itineraries", pool)
    metrics = [replace(m, eligible_itineraries=eligible[m.airport]) for m in metrics]
    result = select_hubs(metrics, cfg.hubs)

    models_to_table(con, "hub_candidates", HubCandidate, result.candidates)
    write_table(
        con, "hub_candidates", derived(cfg, "hub_candidates.parquet"), HubCandidate, ["rank"]
    )
    models_to_table(con, "hub_selection", HubSelection, result.selection)
    write_table(
        con,
        "hub_selection",
        derived(cfg, "hub_selection.parquet"),
        HubSelection,
        ["selected DESC", "airport"],
    )
    codes = [
        r[0]
        for r in con.execute(
            "SELECT origin FROM flights UNION SELECT dest FROM flights ORDER BY 1"
        ).fetchall()
    ]
    tz = {
        code: entry.tz
        for code, entry in AirportsDataTimezones(cfg.timezones.overrides).lookup(codes).items()
    }
    airports = assign_roles(codes, tz, pool, result.selected)
    models_to_table(con, "airports", Airport, airports)
    write_table(con, "airports", derived(cfg, "airports.parquet"), Airport, ["code"])
    write_json(
        derived(cfg, "hub_selection.json"),
        {
            "pool": pool,
            "selected": result.selected,
            "unmet_constraints": result.unmet,
            "median_weather_share": round(result.median_weather_share, 6),
        },
        HubSelectionMeta,
    )
    unmet = f"; unmet: {', '.join(result.unmet)}" if result.unmet else ""
    return f"selected {len(result.selected)} hubs: {', '.join(result.selected)}{unmet}"


def stage_build(con: duckdb.DuckDBPyConnection, cfg: Config) -> str:
    """Itineraries through the selected hubs and the origin/destination pair selection."""
    load_flights(con, cfg)
    hub_meta = read_json(derived(cfg, "hub_selection.json"), HubSelectionMeta)
    hubs, pool = hub_meta["selected"], hub_meta["pool"]
    load_slots(con, cfg)
    nonstop_medians(con, "flights", cfg.period.dates(), "nonstop")
    write_table(con, "nonstop", derived(cfg, "nonstop.parquet"), NonstopMedian, ["origin", "dest"])
    build_itineraries(
        con,
        "slots",
        hubs,
        cfg.itineraries,
        "itineraries",
        flights="flights",
        sold="sold_routings",
        period=cfg.period.dates(),
        days=False,
    )
    write_table(
        con, "itineraries", derived(cfg, "itineraries.parquet"), Itinerary, ["itinerary_id"]
    )
    comparable_candidates(
        con,
        "itineraries",
        cfg.comparison.travel_time_tolerance_min,
        cfg.comparison.departure_window_min,
        "comparable_all",
    )
    rows = select_od_pairs(
        od_candidates(con, "itineraries", "comparable_all"), hubs, cfg.selection, pool=pool
    )
    models_to_table(con, "od_selection", OdSelection, rows)
    write_table(con, "od_selection", derived(cfg, "od_selection.parquet"), OdSelection, ["rank"])
    con.execute("CREATE OR REPLACE TEMP TABLE _chosen (origin VARCHAR, dest VARCHAR)")
    chosen_pairs = sorted((r.origin, r.dest) for r in rows if r.selected)
    if chosen_pairs:
        con.executemany("INSERT INTO _chosen VALUES (?, ?)", chosen_pairs)
    con.execute(
        "CREATE OR REPLACE TABLE od_exclusions AS SELECT e.* FROM itineraries_exclusions e "
        "JOIN _chosen c USING (origin, dest)"
    )
    write_table(
        con,
        "od_exclusions",
        derived(cfg, "od_exclusions.parquet"),
        OdExclusions,
        ["origin", "dest"],
    )
    _write_itinerary_days(con, cfg, hubs, chosen_pairs)
    shortfalls = selection_shortfalls(rows, cfg.selection)
    write_json(derived(cfg, "od_selection.json"), {"shortfalls": shortfalls}, OdSelectionMeta)
    chosen = [r for r in rows if r.selected]
    n_it = con.execute("SELECT count(*) FROM itineraries").fetchone()
    note = f"; {'; '.join(shortfalls)}" if shortfalls else ""
    return (
        f"built {n_it[0] if n_it else 0} itineraries through {len(hubs)} hubs; "
        f"selected {len(chosen)} origin/destination pairs "
        f"({sum(r.regional_origin for r in chosen)} regional){note}"
    )


def _write_itinerary_days(
    con: duckdb.DuckDBPyConnection,
    cfg: Config,
    hubs: Sequence[str],
    pairs: Sequence[tuple[str, str]],
) -> None:
    """itinerary_days.parquet for the selected pairs only: their daily matching, rebuilt for
    those pairs (the full year's matching of every itinerary is too large to keep). The
    rebuilt itineraries must equal the full build's for those pairs."""
    build_itineraries(
        con,
        "slots",
        hubs,
        cfg.itineraries,
        "chosen_itineraries",
        flights="flights",
        sold="sold_routings",
        period=cfg.period.dates(),
        od_pairs=list(pairs),
    )
    differing = con.execute(
        "SELECT count(*) FROM ((SELECT * FROM chosen_itineraries EXCEPT ALL "
        "SELECT i.* FROM itineraries i JOIN _chosen c USING (origin, dest)) UNION ALL "
        "(SELECT i.* FROM itineraries i JOIN _chosen c USING (origin, dest) EXCEPT ALL "
        "SELECT * FROM chosen_itineraries))"
    ).fetchone()
    if differing and differing[0]:
        raise RuntimeError(
            f"rebuilt itineraries of the selected pairs differ in {differing[0]} rows"
        )
    con.execute(
        "CREATE OR REPLACE TABLE itinerary_days AS SELECT itinerary_id, service_date, "
        "match_status, CASE WHEN match_status_ok THEN "
        "CAST((epoch(out_dep) - epoch(in_arr)) // 60 AS INTEGER) END AS sched_layover_min "
        "FROM chosen_itineraries_days"
    )
    write_table(
        con,
        "itinerary_days",
        derived(cfg, "itinerary_days.parquet"),
        ItineraryDay,
        ["itinerary_id", "service_date"],
    )


def _tight(
    con: duckdb.DuckDBPyConnection, cfg: Config, itineraries: Sequence[Itinerary]
) -> set[str]:
    """Tight itineraries (``compare.tight_itineraries``), with the share of connecting days
    scheduled below the threshold from itinerary_days.parquet when the configuration sets
    ``[showcase] tight_day_share_max``."""
    cutoff = cfg.feasibility.boarding_cutoff_min
    limit = cfg.showcase.tight_day_share_max
    path = derived(cfg, "itinerary_days.parquet")
    if not path.exists():
        return tight_itineraries(itineraries, cfg.itineraries, cutoff)
    con.execute("CREATE OR REPLACE TEMP TABLE _thresholds (itinerary_id VARCHAR, t INTEGER)")
    rows = [
        (i.itinerary_id, feasibility_threshold(i, cfg.itineraries, cutoff)) for i in itineraries
    ]
    for start in range(0, len(rows), 500):
        batch = rows[start : start + 500]
        con.execute(
            "INSERT INTO _thresholds VALUES " + ", ".join("(?, ?)" for _ in batch),
            [v for row in batch for v in row],
        )
    below = {
        str(iid): float(share)
        for iid, share in con.execute(
            "SELECT d.itinerary_id, avg(CAST(d.sched_layover_min < t.t AS INTEGER)) "
            f"FROM read_parquet('{path.as_posix()}') d JOIN _thresholds t USING (itinerary_id) "
            "WHERE d.match_status = 'connects' GROUP BY 1"
        ).fetchall()
    }
    return tight_itineraries(
        itineraries, cfg.itineraries, cutoff, days_below=below, max_day_share=limit
    )


def _defaults(cfg: Config) -> tuple[int, int, float]:
    return (
        cfg.itineraries.min_connection_default_min,
        cfg.feasibility.boarding_cutoff_min,
        cfg.itineraries.recurrence_threshold,
    )


def stage_analyze(con: duckdb.DuckDBPyConnection, cfg: Config) -> str:
    """Daily outcomes and results for every scenario, comparable pairs with paired-bootstrap
    intervals, assumption-sensitivity flags and showcase examples."""
    load_flights(con, cfg)
    hubs = read_json(derived(cfg, "hub_selection.json"), HubSelectionMeta)["selected"]
    od_rows = read_models(con, derived(cfg, "od_selection.parquet"), OdSelection)
    pairs = [(r.origin, r.dest) for r in od_rows if r.selected]
    read_table(con, derived(cfg, "itineraries.parquet"), "itineraries")
    period = cfg.period.dates()
    load_slots(con, cfg)
    defaults = _defaults(cfg)
    default_id = scenario_id(*defaults)
    missing = evaluate_scenarios(
        con,
        "flights",
        "slots",
        hubs,
        pairs,
        cfg.itineraries,
        cfg.sensitivity,
        defaults,
        cfg.feasibility.min_sample_days,
        period,
        "results_all",
        "classified_default",
        sold="sold_routings",
    )
    scenario_rows = scenarios(cfg.sensitivity, defaults)
    validate_scenarios(scenario_rows)
    models_to_table(con, "scenarios", SensitivityScenario, scenario_rows)
    write_table(
        con,
        "scenarios",
        derived(cfg, "sensitivity_scenarios.parquet"),
        SensitivityScenario,
        ["scenario_id"],
    )
    con.execute(
        "CREATE OR REPLACE TABLE daily_outcomes AS SELECT itinerary_id, service_date, "
        "raw_slack_min, outcome FROM classified_default WHERE status = 'paired'"
    )
    write_table(
        con,
        "daily_outcomes",
        derived(cfg, "daily_outcomes.parquet"),
        DailyOutcome,
        ["itinerary_id", "service_date"],
    )
    write_table(
        con,
        "results_all",
        derived(cfg, "itinerary_results.parquet"),
        ItineraryResult,
        ["scenario_id", "itinerary_id"],
    )

    # Comparable pairs among the default itineraries of the selected pairs
    con.execute(
        "CREATE OR REPLACE TABLE default_itineraries AS SELECT i.* FROM itineraries i "
        "JOIN results_all_itineraries s ON s.itinerary_id = i.itinerary_id "
        f"WHERE s.scenario_id = '{default_id}'"
    )
    comparable_candidates(
        con,
        "default_itineraries",
        cfg.comparison.travel_time_tolerance_min,
        cfg.comparison.departure_window_min,
        "comparable",
    )
    rates: dict[str, dict[str, float | None]] = {}
    status: dict[str, bool] = {}
    for sid, iid, rate, st in con.execute(
        "SELECT scenario_id, itinerary_id, feasibility_rate, status FROM results_all"
    ).fetchall():
        rates.setdefault(sid, {})[iid] = rate
        if sid == default_id:
            status[iid] = st == "ok"
    raw_pairs = con.execute(
        "SELECT itinerary_x, itinerary_y, travel_diff_min, dep_diff_min FROM comparable"
    ).fetchall()
    flags, scenario_gaps = reversal_flags(
        [(x, y) for x, y, *_ in raw_pairs],
        rates,
        default_id,
        [s.scenario_id for s in scenario_rows],
    )
    settings = settings_compared([(x, y) for x, y, *_ in raw_pairs], rates, scenario_rows)
    other_scenarios = len(scenario_rows) - 1
    gaps: dict[tuple[str, str], int] = {}
    for gx, gy, _sid in scenario_gaps:
        gaps[(gx, gy)] = gaps.get((gx, gy), 0) + 1
    days: dict[str, dict[dt.date, bool]] = {}
    for iid, day, outcome in con.execute(
        "SELECT itinerary_id, service_date, outcome FROM classified_default WHERE status = 'paired'"
    ).fetchall():
        days.setdefault(iid, {})[day] = outcome == "feasible"
    base = rates.get(default_id, {})
    ordered = [order_pair(x, y, base.get(x), base.get(y)) for x, y, *_ in raw_pairs]
    tasks: list[BootstrapTask] = [
        (
            days.get(a, {}),
            days.get(b, {}),
            cfg.comparison.bootstrap_resamples,
            cfg.comparison.ci_level,
            cfg.seed,
            f"{a}|{b}",
        )
        for a, b in ordered
        if status.get(a, False) and status.get(b, False)
    ]
    intervals = dict(zip((t[5] for t in tasks), paired_bootstraps(tasks), strict=True))
    out_pairs: list[ComparablePair] = []
    for (x, y, travel_diff, dep_diff_), (a, b) in zip(raw_pairs, ordered, strict=True):
        ra, rb = base.get(a), base.get(b)
        low, high = intervals.get(f"{a}|{b}", (None, None))
        diff = None if ra is None or rb is None else round(ra - rb, 6)
        common = shared_days(days.get(a, {}), days.get(b, {}))
        sensitive = flags[(x, y)]
        out_pairs.append(
            ComparablePair(
                itinerary_a=a,
                itinerary_b=b,
                travel_diff_min=int(travel_diff),
                dep_diff_min=int(dep_diff_),
                rate_diff=diff,
                scenarios_compared=other_scenarios - gaps.get((x, y), 0),
                settings_compared=settings[(x, y)],
                shared_days=common,
                ci_low=low,
                ci_high=high,
                assumption_sensitive=sensitive,
                showcase=is_showcase(
                    rate_a=ra,
                    rate_b=rb,
                    sufficient_a=status.get(a, False),
                    sufficient_b=status.get(b, False),
                    ci_low=low,
                    ci_high=high,
                    assumption_sensitive=sensitive,
                    gap=cfg.comparison.showcase_gap,
                    shared_days=common,
                    min_shared_days=cfg.feasibility.min_sample_days,
                ),
            )
        )
    models_to_table(con, "comparable_pairs", ComparablePair, out_pairs)
    write_table(
        con,
        "comparable_pairs",
        derived(cfg, "comparable_pairs.parquet"),
        ComparablePair,
        ["itinerary_a", "itinerary_b"],
    )
    write_json(
        derived(cfg, "sensitivity.json"),
        {
            "pairs_without_itineraries": missing,
            "pair_scenarios_not_comparable": len(scenario_gaps),
        },
        SensitivityMeta,
    )
    n_ok = sum(status.values())
    showcases = sum(p.showcase for p in out_pairs)
    return (
        f"analyzed {len(status)} itineraries in {len(pairs)} pairs ({n_ok} with sufficient "
        f"data) under {len(scenario_rows)} scenarios; {len(out_pairs)} comparable pairs, "
        f"{sum(p.assumption_sensitive for p in out_pairs)} assumption-sensitive, "
        f"{showcases} showcase examples"
    )


# --- Curation ----------------------------------------------------------------------------


def stage_curate(con: duckdb.DuckDBPyConnection, cfg: Config) -> str:
    """Showcase routes, balanced showcase comparisons and the landing example (research R4)."""
    od_rows = read_models(con, derived(cfg, "od_selection.parquet"), OdSelection)
    itineraries = read_models(con, derived(cfg, "itineraries.parquet"), Itinerary)
    pairs = read_models(con, derived(cfg, "comparable_pairs.parquet"), ComparablePair)
    scenario_rows = read_models(
        con, derived(cfg, "sensitivity_scenarios.parquet"), SensitivityScenario
    )
    by_id = {i.itinerary_id: i for i in itineraries}
    tight = _tight(con, cfg, itineraries)
    counts: dict[str, int] = {}
    for i in itineraries:
        counts[f"{i.origin}-{i.dest}"] = counts.get(f"{i.origin}-{i.dest}", 0) + 1
    routes = [
        RouteCandidate(
            route_id=f"{r.origin}-{r.dest}",
            origin=r.origin,
            dest=r.dest,
            regional_origin=r.regional_origin,
            itinerary_count=counts.get(f"{r.origin}-{r.dest}", 0),
        )
        for r in od_rows
        if r.selected
    ]
    comps: list[CandidateComparison] = []
    for p in pairs:
        if not p.showcase or p.rate_diff is None:
            continue
        a, b = by_id[p.itinerary_a], by_id[p.itinerary_b]
        lower = b if p.rate_diff > 0 else a
        comps.append(
            CandidateComparison(
                comparison_id=f"{a.itinerary_id}|{b.itinerary_id}",
                route_id=f"{a.origin}-{a.dest}",
                itinerary_a=a.itinerary_id,
                itinerary_b=b.itinerary_id,
                airlines=frozenset({a.airline_in, a.airline_out, b.airline_in, b.airline_out}),
                hubs=frozenset({a.hub, b.hub}),
                cross_hub=a.hub != b.hub,
                difference=abs(p.rate_diff),
                settings_compared=p.settings_compared,
                lower_tight=lower.itinerary_id in tight,
            )
        )
    total_settings = len({(s.min_connection_min, s.boarding_cutoff_min) for s in scenario_rows})
    result = curate(routes, comps, cfg.showcase, total_settings)
    models_to_table(
        con,
        "showcase_routes",
        CuratedRouteRow,
        [CuratedRouteRow(**asdict(r)) for r in result.routes],
    )
    write_table(
        con,
        "showcase_routes",
        derived(cfg, "showcase_routes.parquet"),
        CuratedRouteRow,
        ["rank"],
    )
    models_to_table(
        con,
        "showcase_comparisons",
        CuratedComparisonRow,
        [CuratedComparisonRow(**asdict(c)) for c in result.comparisons],
    )
    write_table(
        con,
        "showcase_comparisons",
        derived(cfg, "showcase_comparisons.parquet"),
        CuratedComparisonRow,
        ["comparison_id"],
    )
    write_json(
        derived(cfg, "curation.json"),
        {
            "landing_comparison_id": result.landing_comparison_id,
            "landing_reason": result.landing_reason,
            "airline_shares": result.airline_shares,
            "hub_shares": result.hub_shares,
            "cross_hub_share": result.cross_hub_share,
            "shortfalls": result.shortfalls,
        },
        CurationMeta,
    )
    for s in result.shortfalls:
        print(f"curate: shortfall: {s}", file=sys.stderr, flush=True)
    return (
        f"curated {len(result.routes)} routes and {len(result.comparisons)} showcase "
        f"comparisons ({result.cross_hub_share:.0%} cross-hub); landing "
        f"{result.landing_comparison_id or 'none'}; {len(result.shortfalls)} shortfall(s)"
    )


# --- Insights ----------------------------------------------------------------------------


def stage_insights(con: duckdb.DuckDBPyConnection, cfg: Config) -> str:
    """Traveler insights for every itinerary on a curated route (specs/002 User Story 5)."""
    routes = {
        r.route_id
        for r in read_models(con, derived(cfg, "showcase_routes.parquet"), CuratedRouteRow)
    }
    its = [
        i
        for i in read_models(con, derived(cfg, "itineraries.parquet"), Itinerary)
        if f"{i.origin}-{i.dest}" in routes
    ]
    ids = {i.itinerary_id for i in its}
    default_id = scenario_id(*_defaults(cfg))
    results = {
        r.itinerary_id: r
        for r in read_models(con, derived(cfg, "itinerary_results.parquet"), ItineraryResult)
        if r.scenario_id == default_id and r.itinerary_id in ids
    }
    daily = _daily_by_itinerary(
        read_models(con, derived(cfg, "daily_outcomes.parquet"), DailyOutcome), results
    )
    matched: dict[str, list[ItineraryDay]] = {}
    for x in read_models(
        con, derived(cfg, "itinerary_days.parquet"), ItineraryDay, only=("itinerary_id", ids)
    ):
        if x.itinerary_id in ids:
            matched.setdefault(x.itinerary_id, []).append(x)
    slot_ids = {s for i in its for s in (i.inbound_slot, i.outbound_slot)}
    slot_days: dict[str, list[tuple[dt.date, int]]] = {}
    for d in read_models(
        con, derived(cfg, "slots_days.parquet"), SlotDay, only=("slot_id", slot_ids)
    ):
        if d.slot_id in slot_ids:
            slot_days.setdefault(d.slot_id, []).append((d.service_date, d.dep_local_min))
    joins: dict[str, list[tuple[dt.date, int, int]]] = {}
    for c in read_models(con, derived(cfg, "slots_changes.parquet"), SlotChange):
        if c.slot_id in slot_ids:
            joins.setdefault(c.slot_id, []).append(
                (c.change_date, c.from_local_min, c.to_local_min)
            )
    slots = {
        s.slot_id: SlotData(
            slot=s, days=slot_days.get(s.slot_id, []), joins=joins.get(s.slot_id, [])
        )
        for s in read_models(con, derived(cfg, "slots.parquet"), ScheduleSlot)
        if s.slot_id in slot_ids
    }
    data = {
        i.itinerary_id: ItineraryData(
            itinerary=i,
            result=results[i.itinerary_id],
            daily=daily.get(i.itinerary_id, []),
            days=matched.get(i.itinerary_id, []),
        )
        for i in its
    }
    notes = load_disruption_notes(cfg.path(cfg.notes.disruption_file), cfg.period.dates())
    result = build_insights(data, slots, notes, cfg)
    write_json(derived(cfg, "insights.json"), result.model_dump(mode="json"), InsightsFile)
    rows = result.itineraries.values()
    return (
        f"insights for {len(rows)} itineraries on {len(routes)} routes: "
        f"{sum(bool(x.faster_alternatives) for x in rows)} with a faster alternative, "
        f"{sum(any(o.better for o in x.connecting_options) for x in rows)} with a better "
        f"connecting option, {sum(bool(x.schedule_warnings.changes) for x in rows)} with a "
        "schedule change"
    )


# --- Publish -----------------------------------------------------------------------------


def _daily_by_itinerary(
    rows: list[DailyOutcome], keep: Mapping[str, Any]
) -> dict[str, list[DailyOutcome]]:
    out: dict[str, list[DailyOutcome]] = {}
    for r in rows:
        if r.itinerary_id in keep:
            out.setdefault(r.itinerary_id, []).append(r)
    return out


def stage_publish(con: duckdb.DuckDBPyConnection, cfg: Config, config_path: Path) -> str:
    """Write the validated, size-budgeted showcase JSON (specs/002 contracts/outputs.md)."""
    routes = read_models(con, derived(cfg, "showcase_routes.parquet"), CuratedRouteRow)
    comps = read_models(con, derived(cfg, "showcase_comparisons.parquet"), CuratedComparisonRow)
    meta = read_json(derived(cfg, "curation.json"), CurationMeta)
    itineraries = read_models(con, derived(cfg, "itineraries.parquet"), Itinerary)
    results = read_models(con, derived(cfg, "itinerary_results.parquet"), ItineraryResult)
    pairs = read_models(con, derived(cfg, "comparable_pairs.parquet"), ComparablePair)
    scenario_rows = read_models(
        con, derived(cfg, "sensitivity_scenarios.parquet"), SensitivityScenario
    )
    nonstop = read_models(con, derived(cfg, "nonstop.parquet"), NonstopMedian)
    hubs = read_json(derived(cfg, "hub_selection.json"), HubSelectionMeta)["selected"]
    for name in ("flights", "sold_routings", "slots", "slots_days"):
        path = derived(cfg, f"{name}.parquet").as_posix().replace("'", "''")
        con.execute(f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM read_parquet('{path}')")

    default_id = scenario_id(*_defaults(cfg))
    shown_routes = {r.route_id for r in routes}
    shown = {i.itinerary_id: i for i in itineraries if f"{i.origin}-{i.dest}" in shown_routes}
    rates_by_scenario: dict[str, dict[str, float | None]] = {}
    for r in results:
        rates_by_scenario.setdefault(r.scenario_id, {})[r.itinerary_id] = r.feasibility_rate
    mcts = sorted({s.min_connection_min for s in scenario_rows})
    cutoffs = sorted({s.boarding_cutoff_min for s in scenario_rows})
    compared = [(c.itinerary_a, c.itinerary_b) for c in comps]
    missing = {
        k: describe_missing_settings(v, mcts, cutoffs)
        for k, v in missing_settings(compared, rates_by_scenario, scenario_rows).items()
    }
    inputs = assemble.Inputs(
        routes=routes,
        comparisons=comps,
        landing_comparison_id=meta["landing_comparison_id"],
        landing_reason=meta["landing_reason"],
        itineraries=shown,
        results={
            r.itinerary_id: r
            for r in results
            if r.scenario_id == default_id and r.itinerary_id in shown
        },
        pairs={(p.itinerary_a, p.itinerary_b): p for p in pairs},
        missing_settings=missing,
        nonstop={(n.origin, n.dest): n for n in nonstop},
        arrival_local_min=assemble.arrival_minutes(con, "slots_days", "flights"),
        insights=InsightsFile.model_validate(
            read_json(derived(cfg, "insights.json"), InsightsFile)
        ).itineraries,
        hubs=hubs,
        sold_same_airline=assemble.sold_same_airline(con, "sold_routings", hubs),
        analysis_itineraries=dict(Counter(i.airline_in for i in itineraries)),
        curation=CurationMeta.model_validate(meta),
        routings_at_minimum=assemble.routings_at_minimum(
            con, "sold_routings", hubs, cfg.itineraries.min_sold_passengers
        ),
        daily=_daily_by_itinerary(
            read_models(con, derived(cfg, "daily_outcomes.parquet"), DailyOutcome), shown
        ),
        tight=frozenset(_tight(con, cfg, list(shown.values()))),
        notes=load_disruption_notes(cfg.path(cfg.notes.disruption_file), cfg.period.dates()),
    )
    route_files = assemble.route_files(inputs, cfg)
    index = assemble.index_of(route_files, inputs, cfg, _sha256(config_path))
    files = render(index, route_files, validation_context(cfg))
    sizes = write_files(
        cfg.path(cfg.showcase.output_dir),
        files,
        cfg.showcase.size_budget_kb,
        cfg.showcase.landing_budget_kb,
    )
    write_showcase_manifest(cfg, config_path, None)
    total = sum(sizes.values()) / 1024
    first = (sizes["index.json"] + sizes["landing.json"]) / 1024
    return (
        f"published {len(route_files)} route files and "
        f"{sum(len(r.itineraries) for r in route_files)} itineraries; "
        f"{total:.1f} KB gzip in all, {first:.1f} KB for index and landing"
    )


SHOWCASE_MANIFEST = "manifest.json"


def showcase_outputs(out_dir: Path) -> dict[str, str]:
    """sha256 of every published file except the manifest, by path relative to ``out_dir``."""
    return {
        p.relative_to(out_dir).as_posix(): _sha256(p)
        for p in sorted(out_dir.rglob("*.json"))
        if p.name != SHOWCASE_MANIFEST or p.parent != out_dir
    }


def showcase_manifest(
    previous: dict[str, Any] | None,
    *,
    identity: dict[str, Any],
    outputs: dict[str, str],
    run: dict[str, Any],
) -> dict[str, Any]:
    """The showcase manifest (FR-027): ``identity`` holds sources, config and notes checksums,
    packages, code version and git commit. A measured runtime is carried over from
    ``previous`` only when every identity field matches (the Phase 0 rule, extended to the
    code version)."""
    same = previous is not None and all(previous.get(k) == v for k, v in identity.items())
    return {
        **identity,
        "outputs": outputs,
        "run": merge_run(previous and previous.get("run"), run, same_inputs=same),
    }


def write_showcase_manifest(
    cfg: Config, config_path: Path, runtime_min: float | None
) -> dict[str, Any]:
    out_dir = cfg.path(cfg.showcase.output_dir)
    version, commit = assemble.code_identity(cfg.repo_root)
    identity: dict[str, Any] = {
        "sources": source_records(cfg),
        "config_sha256": _sha256(config_path),
        "notes_sha256": _sha256(cfg.path(cfg.notes.disruption_file)),
        "code_version": version,
        "git_commit": commit,
        "packages": {
            **{p: metadata.version(p) for p in PACKAGES},
            "python": ".".join(map(str, sys.version_info[:2])),
        },
    }
    run = {
        "run_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "runtime_min": None if runtime_min is None else round(runtime_min, 2),
        "runtime_limit_min": cfg.runtime.limit_min,
        "runtime_exceeded": None if runtime_min is None else runtime_min > cfg.runtime.limit_min,
        "machine": _machine(),
    }
    path = out_dir / SHOWCASE_MANIFEST
    previous = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    manifest = showcase_manifest(
        previous, identity=identity, outputs=showcase_outputs(out_dir), run=run
    )
    write_json(path, manifest, ShowcaseManifest)
    return manifest


# --- Report and manifest -----------------------------------------------------------------

DERIVED_TABLES = (
    "flights.parquet",
    "slots.parquet",
    "slots_days.parquet",
    "slots_changes.parquet",
    "nonstop.parquet",
    "passengers.parquet",
    "sold_routings.parquet",
    "airports.parquet",
    "hub_candidates.parquet",
    "hub_selection.parquet",
    "itineraries.parquet",
    "itinerary_days.parquet",
    "od_selection.parquet",
    "od_exclusions.parquet",
    "sensitivity_scenarios.parquet",
    "daily_outcomes.parquet",
    "itinerary_results.parquet",
    "comparable_pairs.parquet",
    "showcase_routes.parquet",
    "showcase_comparisons.parquet",
)
REPORT_FILES = ("summary.json", "summary.md", "quality.json")
PACKAGES = ("flight-pipeline", "duckdb", "pydantic", "numpy", "airportsdata", "tzdata", "httpx")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _machine() -> dict[str, Any]:
    """The machine the run was timed on, with the thread limit when one was set (SC-008:
    a run limited to 4 threads stands in for the 4-core reference machine)."""
    threads = os.environ.get(THREADS_ENV)
    return {
        "cpu_count": os.cpu_count(),
        "ram_gb": _ram_gb(),
        "thread_limit": int(threads) if threads else None,
    }


def _ram_gb() -> float | None:
    try:
        if sys.platform == "win32":
            import ctypes

            class _Mem(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            mem = _Mem()
            mem.dwLength = ctypes.sizeof(_Mem)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))  # type: ignore[attr-defined]
            return round(mem.ullTotalPhys / 2**30, 1)
        pages = os.sysconf("SC_PHYS_PAGES")
        size = os.sysconf("SC_PAGE_SIZE")
        return round(pages * size / 2**30, 1)
    except (OSError, ValueError, AttributeError):
        return None


def source_records(cfg: Config) -> list[dict[str, Any]]:
    """Source files and checksums: from ``sources.json`` written by ``acquire``, or computed
    from the raw CSV files when the run started from files already in place."""
    raw = cfg.path(cfg.paths.raw_dir)
    recorded = raw / "sources.json"
    if recorded.exists():
        data = json.loads(recorded.read_text(encoding="utf-8"))
        return [
            {"name": d["name"], "sha256": d["sha256"], "pinned": d["pinned"]}
            for d in sorted(data, key=lambda d: d["name"])
        ]
    files = sorted((raw / "ontime").glob("*.csv"))
    t100 = cfg.path(cfg.sources.t100.manual_file)
    out = [{"name": f"ontime/{f.stem}", "sha256": _sha256(f), "pinned": False} for f in files]
    out += [
        {"name": f"db1b/{f.stem}", "sha256": _sha256(f), "pinned": False}
        for f in sorted((raw / "db1b").glob("*.zip"))
    ]
    if t100.exists():
        out.append({"name": "t100", "sha256": _sha256(t100), "pinned": False})
    return out


def output_hashes(con: duckdb.DuckDBPyConnection, cfg: Config) -> dict[str, str]:
    out: dict[str, str] = {}
    for name in DERIVED_TABLES:
        path = derived(cfg, name)
        if path.exists():
            out[name] = _sha256(path)  # byte-identical by design (research R8)
    for name in REPORT_FILES:
        path = reports(cfg, name)
        if path.exists():
            out[name] = _sha256(path)
    return out


def write_manifest(
    con: duckdb.DuckDBPyConnection,
    cfg: Config,
    config_path: Path,
    runtime_min: float | None,
) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "config_sha256": _sha256(config_path),
        "sources": source_records(cfg),
        "packages": {
            **{p: metadata.version(p) for p in PACKAGES},
            "python": ".".join(map(str, sys.version_info[:2])),
        },
        "outputs": output_hashes(con, cfg),
        # Run-specific fields: never part of any output hash.
        "run": {
            "run_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
            "runtime_min": None if runtime_min is None else round(runtime_min, 2),
            "runtime_limit_min": cfg.runtime.limit_min,
            "runtime_exceeded": None
            if runtime_min is None
            else runtime_min > cfg.runtime.limit_min,
            "machine": _machine(),
        },
    }
    path = reports(cfg, "manifest.json")
    old: dict[str, Any] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    same = all(old.get(k) == manifest[k] for k in ("config_sha256", "sources"))
    manifest["run"] = merge_run(old.get("run"), manifest["run"], same_inputs=same)
    write_json(path, manifest, Manifest)
    return manifest


def merge_run(
    previous: dict[str, Any] | None, new: dict[str, Any], *, same_inputs: bool
) -> dict[str, Any]:
    """The manifest's run block. A full ``run`` measures its runtime (SC-008); a stage run on
    its own (for example ``report``) keeps the runtime of the last full run, and says when it
    was measured, but only when the configuration and sources are unchanged
    (``same_inputs``); otherwise the runtime is recorded as not measured."""
    if new.get("runtime_min") is not None:
        return {**new, "runtime_measured_at": new["run_at"]}
    if same_inputs and previous and previous.get("runtime_min") is not None:
        return {
            **new,
            "runtime_min": previous["runtime_min"],
            "runtime_exceeded": previous.get("runtime_exceeded"),
            "runtime_measured_at": previous.get("runtime_measured_at", previous.get("run_at")),
            "machine": previous.get("machine", new.get("machine")),
        }
    return {**new, "runtime_measured_at": None}


def scenario_summaries(
    results: list[ItineraryResult],
    scenario_rows: list[SensitivityScenario],
    pairs: list[ComparablePair],
    default_id: str,
) -> list[dict[str, Any]]:
    rates: dict[str, dict[str, float | None]] = {}
    for r in results:
        rates.setdefault(r.scenario_id, {})[r.itinerary_id] = r.feasibility_rate
    rates.setdefault(default_id, {})
    reversals = reversals_by_scenario(
        [(p.itinerary_a, p.itinerary_b) for p in pairs], rates, default_id
    )
    out: list[dict[str, Any]] = []
    for s in scenario_rows:
        rows = [r for r in results if r.scenario_id == s.scenario_id]
        ok = [r.feasibility_rate for r in rows if r.feasibility_rate is not None]
        out.append(
            {
                "scenario_id": s.scenario_id,
                "is_default": s.is_default,
                "min_connection_min": s.min_connection_min,
                "boarding_cutoff_min": s.boarding_cutoff_min,
                "recurrence_threshold": s.recurrence_threshold,
                "itineraries": len(rows),
                "sufficient": len(ok),
                "median_rate": statistics.median(ok) if ok else None,
                "reversals": reversals.get(s.scenario_id, 0),
            }
        )
    return out


def _report_title(config_path: Path) -> str:
    """Phase 0's title for its frozen report; Phase 1's for its rerun. Taken from the
    configuration file's name, which ``verify`` shares (its output directories differ)."""
    if config_path.stem == "phase1":
        return "Phase 1 rerun: connection feasibility with schedule-slot itineraries"
    return "Phase 0 finding: connection feasibility experiment"


def _curation_sections(con: duckdb.DuckDBPyConnection, cfg: Config) -> list[str]:
    """The showcase curation section, when the curate stage has run (Phase 1)."""
    path = derived(cfg, "curation.json")
    if not path.exists():
        return []
    meta = read_json(path, CurationMeta)
    routes = read_models(con, derived(cfg, "showcase_routes.parquet"), CuratedRouteRow)
    sc = cfg.showcase
    return [
        curation_section(
            [(r.route_id, r.comparison_count, r.share_of_showcase) for r in routes],
            meta["airline_shares"],
            meta["hub_shares"],
            meta["cross_hub_share"],
            meta["shortfalls"],
            (sc.max_share_route, sc.max_share_airline, sc.max_share_hub, sc.cross_hub_share_min),
        )
    ]


def stage_report(
    con: duckdb.DuckDBPyConnection,
    cfg: Config,
    config_path: Path,
    runtime_min: float | None = None,
) -> str:
    """summary.json (Finding), summary.md and manifest.json."""
    hub_meta = read_json(derived(cfg, "hub_selection.json"), HubSelectionMeta)
    candidates = read_models(con, derived(cfg, "hub_candidates.parquet"), HubCandidate)
    selection = read_models(con, derived(cfg, "hub_selection.parquet"), HubSelection)
    od_rows = read_models(con, derived(cfg, "od_selection.parquet"), OdSelection)
    od_meta = read_json(derived(cfg, "od_selection.json"), OdSelectionMeta)
    itineraries = read_models(con, derived(cfg, "itineraries.parquet"), Itinerary)
    results = read_models(con, derived(cfg, "itinerary_results.parquet"), ItineraryResult)
    pairs = read_models(con, derived(cfg, "comparable_pairs.parquet"), ComparablePair)
    scenario_rows = read_models(
        con, derived(cfg, "sensitivity_scenarios.parquet"), SensitivityScenario
    )
    sens_meta = read_json(derived(cfg, "sensitivity.json"), SensitivityMeta)
    quality = read_json(reports(cfg, "quality.json"), QualitySummary)
    db1b = read_json(derived(cfg, "sold_routings.json"), SoldRoutingsSummary)
    exclusions = read_models(con, derived(cfg, "od_exclusions.parquet"), OdExclusions)

    default_id = scenario_id(*_defaults(cfg))
    default_results = [r for r in results if r.scenario_id == default_id]
    by_id = {r.itinerary_id: r for r in default_results}
    hub_of = {i.itinerary_id: i.hub for i in itineraries}
    selected_pairs = {(r.origin, r.dest) for r in od_rows if r.selected}
    counts: dict[tuple[str, str], int] = {}
    for r in default_results:
        it = r.itinerary_id.split(":", 1)[0].split("-")
        counts[(it[0], it[2])] = counts.get((it[0], it[2]), 0) + 1
    examples = [p for p in pairs if p.showcase]
    example_hubs = {
        h for p in examples for h in (hub_of_id(p.itinerary_a), hub_of_id(p.itinerary_b))
    }
    met_examples, met_hubs = go_criteria(
        [(hub_of_id(p.itinerary_a), hub_of_id(p.itinerary_b)) for p in examples],
        cfg.comparison.go_min_examples,
        cfg.comparison.go_min_hubs,
    )
    # Unmapped DB1B selling airlines and nonstop times, straight from the derived tables
    for name in ("flights", "sold_routings"):
        path = derived(cfg, f"{name}.parquet").as_posix().replace("'", "''")
        con.execute(f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM read_parquet('{path}')")
    unmapped, unmapped_pax = unmapped_airlines(con, "sold_routings", "flights")
    two_coupon = int(db1b["two_coupon_passengers"])
    # median scheduled nonstop time per airport pair, any airline
    nonstop = {
        (str(o), str(d)): int(m)
        for o, d, m in con.execute(
            "SELECT origin, dest, quantile_disc(sched_elapsed_min, 0.5) FROM flights "
            "WHERE quality_flag <> 'duplicate' GROUP BY ALL"
        ).fetchall()
    }
    rates_by_scenario: dict[str, dict[str, float | None]] = {}
    for r in results:
        rates_by_scenario.setdefault(r.scenario_id, {})[r.itinerary_id] = r.feasibility_rate
    mcts = sorted({s.min_connection_min for s in scenario_rows})
    cutoffs = sorted({s.boarding_cutoff_min for s in scenario_rows})
    missing = {
        k: describe_missing_settings(v, mcts, cutoffs)
        for k, v in missing_settings(
            [(p.itinerary_a, p.itinerary_b) for p in examples], rates_by_scenario, scenario_rows
        ).items()
    }
    tight_ids = _tight(con, cfg, itineraries)
    by_itinerary = {i.itinerary_id: i for i in itineraries}
    breakdown = (
        showcase_breakdown(
            examples, by_itinerary, tight=tight_ids, nonstop_min=nonstop, missing_settings=missing
        )
        if examples
        else None
    )
    con.execute("CREATE OR REPLACE TEMP TABLE _sel_hubs (hub VARCHAR)")
    con.executemany(
        "INSERT INTO _sel_hubs VALUES (?)", [(s.airport,) for s in selection if s.selected]
    )
    coverage = airline_coverage(
        [i.airline_in for i in itineraries],
        {
            str(a): int(n)
            for a, n in con.execute(
                "SELECT airline_in, CAST(sum(passengers) AS BIGINT) FROM sold_routings "
                "WHERE airline_in = airline_out AND hub IN (SELECT hub FROM _sel_hubs) "
                "GROUP BY 1"
            ).fetchall()
        },
    )
    period_start, period_end = cfg.period.dates()
    finding = Finding(
        ontime_period_start=period_start,
        ontime_period_end=period_end,
        t100_period_start=period_start,
        t100_period_end=period_end,
        db1b_quarters=list(db1b["quarters"]),
        db1b_unknown_airline_share=float(db1b["unknown_airline_share"]),
        db1b_unmapped_airlines=unmapped,
        db1b_unmapped_airline_share=round(unmapped_pax / two_coupon, 6) if two_coupon else 0.0,
        showcase_breakdown=breakdown,
        airline_coverage=coverage,
        od_exclusions=exclusions,
        hubs=[s for s in selection if s.selected],
        unmet_constraints=list(hub_meta["unmet_constraints"]),
        od_pairs=[r for r in od_rows if r.selected],
        od_pairs_without_itineraries=list(sens_meta["pairs_without_itineraries"]),
        default_results=default_results,
        showcase_examples=examples,
        criterion_min_examples_met=met_examples,
        criterion_min_hubs_met=met_hubs,
        decision="go" if met_examples and met_hubs else "no_go",
        ci_method=CI_METHOD.replace(
            "(10,000 times by default, fixed seed)",
            f"({cfg.comparison.bootstrap_resamples:,} times, seed {cfg.seed})",
        ).replace("central percentile range", f"central {round(cfg.comparison.ci_level * 100)}%"),
        limitations=list(LIMITATIONS),
        data_quality={k: int(v) for k, v in quality["totals"].items() if k != "rows"},
    )
    summaries = scenario_summaries(results, scenario_rows, pairs, default_id)
    write_json(derived(cfg, "sensitivity_summary.json"), summaries, SCENARIO_SUMMARIES)
    sections = [
        hub_section(
            candidates,
            selection,
            finding.unmet_constraints,
            float(hub_meta["median_weather_share"]),
            weights=cfg.hubs.weights,
        ),
        airline_section(coverage, recurrence_threshold=cfg.itineraries.recurrence_threshold),
        od_section(od_rows, counts, od_meta["shortfalls"], finding.od_pairs_without_itineraries),
        exclusions_section(
            exclusions,
            min_sold_passengers=cfg.itineraries.min_sold_passengers,
            recurrence_threshold=cfg.itineraries.recurrence_threshold,
        ),
        showcase_section(
            examples,
            by_id,
            hub_of,
            cfg.comparison.ci_level,
            layover={i.itinerary_id: i.median_layover_min for i in itineraries},
            tight=tight_ids,
            total_settings=len(
                {(s.min_connection_min, s.boarding_cutoff_min) for s in scenario_rows}
            ),
            sold={i.itinerary_id: i.sold_passengers for i in itineraries},
            missing_settings=missing,
            routing_itineraries=routing_itineraries(itineraries),
        ),
        *([breakdown_section(breakdown)] if breakdown else []),
        *_curation_sections(con, cfg),
        sensitivity_section(
            summaries,
            [p for p in pairs if p.assumption_sensitive],
            int(sens_meta["pair_scenarios_not_comparable"]),
        ),
    ]
    appendix = [
        results_section(
            [
                r
                for r in default_results
                if (r.itinerary_id.split("-")[0], r.itinerary_id.split(":")[0].split("-")[2])
                in selected_pairs
            ],
            hub_of,
            cfg.feasibility.min_sample_days,
        ),
    ]
    out_dir = cfg.path(cfg.paths.reports_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(finding_json(finding), encoding="utf-8", newline="\n")
    (out_dir / "summary.md").write_text(
        render_summary(
            finding,
            sections,
            cfg.comparison.go_min_examples,
            cfg.comparison.go_min_hubs,
            appendix,
            title=_report_title(config_path),
        ),
        encoding="utf-8",
        newline="\n",
    )
    write_manifest(con, cfg, config_path, runtime_min)
    return (
        f"decision {finding.decision}: {len(examples)} showcase examples "
        f"(min {cfg.comparison.go_min_examples}), "
        f"{len(example_hubs)} hubs (min {cfg.comparison.go_min_hubs})"
    )
