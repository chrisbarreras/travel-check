"""Every insight for every itinerary on a curated route (specs/002 User Story 5)."""

from __future__ import annotations

import datetime as dt
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from flight_pipeline.config import Config, DisruptionNote
from flight_pipeline.insights.alternatives import (
    Bootstrap,
    Facts,
    connecting_options,
    faster_alternatives,
)
from flight_pipeline.insights.buffer import buffer
from flight_pipeline.insights.monthly import failure_breakdown, month_key, monthly_view
from flight_pipeline.insights.schedule import find_params, schedule_changes, schedule_warnings
from flight_pipeline.models import (
    DailyOutcome,
    Itinerary,
    ItineraryDay,
    ItineraryResult,
    ScheduleSlot,
)
from flight_pipeline.showcase.models import InsightsFile, ItineraryInsights, Rate, ScheduleChange

OPERATED = ("feasible", "insufficient_time")


@dataclass(frozen=True)
class ItineraryData:
    itinerary: Itinerary
    result: ItineraryResult  # default scenario
    daily: Sequence[DailyOutcome]  # paired days, default scenario
    days: Sequence[ItineraryDay]  # the default daily matching


@dataclass(frozen=True)
class SlotData:
    slot: ScheduleSlot
    days: Sequence[tuple[dt.date, int]]  # (date, scheduled local departure minute)
    joins: Sequence[tuple[dt.date, int, int]]  # (date, from, to)


def rate_of(r: ItineraryResult) -> Rate:
    ok = r.status == "ok"
    return Rate(
        status=r.status,
        rate=r.feasibility_rate if ok else None,
        paired_days=r.paired_days,
        count_feasible=r.count_feasible,
        definition="connection_feasibility",
    )


def facts_of(d: ItineraryData) -> Facts:
    it = d.itinerary
    return Facts(
        itinerary_id=it.itinerary_id,
        origin=it.origin,
        dest=it.dest,
        inbound_slot=it.inbound_slot,
        outbound_slot=it.outbound_slot,
        dep_local_min=it.median_dep_local_min,
        travel_min=it.median_travel_min,
        rate=rate_of(d.result),
        days={r.service_date: r.outcome == "feasible" for r in d.daily},
    )


def _operated(d: ItineraryData) -> list[tuple[int, int]]:
    layover = {x.service_date: x.sched_layover_min for x in d.days}
    out: list[tuple[int, int]] = []
    for r in d.daily:
        lay = layover.get(r.service_date)
        if r.outcome in OPERATED and r.raw_slack_min is not None and lay is not None:
            out.append((lay, r.raw_slack_min))
    return out


def _monthly(d: ItineraryData, cfg: Config, notes: Sequence[DisruptionNote]):  # type: ignore[no-untyped-def]
    paired: dict[str, tuple[int, int]] = {}
    for r in d.daily:
        n, k = paired.get(month_key(r.service_date), (0, 0))
        paired[month_key(r.service_date)] = (n + 1, k + (r.outcome == "feasible"))
    flown = {month_key(x.service_date) for x in d.days if x.match_status != "end_of_period"}
    it = d.itinerary
    return monthly_view(
        [f"{y:04d}-{m:02d}" for y, m in cfg.period.months()],
        paired,
        flown,
        cfg.insights.monthly_min_sample,
        notes,
        [it.airline_in, it.airline_out],
        [it.origin, it.hub, it.dest],
    )


def build_insights(
    data: Mapping[str, ItineraryData],
    slots: Mapping[str, SlotData],
    notes: Sequence[DisruptionNote],
    cfg: Config,
) -> InsightsFile:
    boot = Bootstrap(
        resamples=cfg.comparison.bootstrap_resamples,
        ci_level=cfg.comparison.ci_level,
        seed=cfg.seed,
        min_shared_days=cfg.feasibility.min_sample_days,
    )
    facts = {k: facts_of(d) for k, d in sorted(data.items())}
    by_route: dict[tuple[str, str], list[Facts]] = {}
    for f in facts.values():
        by_route.setdefault((f.origin, f.dest), []).append(f)
    outbound_dep = {k: s.slot.ref_dep_local_min for k, s in slots.items()}
    ins = cfg.insights
    out: dict[str, ItineraryInsights] = {}
    for key, d in sorted(data.items()):
        it, r, f = d.itinerary, d.result, facts[key]
        peers = by_route[(it.origin, it.dest)]
        threshold = (
            cfg.itineraries.min_connection_for(it.hub, partner=it.partner_connection)
            + cfg.feasibility.boarding_cutoff_min
        )
        legs: list[list[ScheduleChange]] = []
        for slot_id, leg in ((it.inbound_slot, "inbound"), (it.outbound_slot, "outbound")):
            s = slots[slot_id]
            legs.append(
                schedule_changes(
                    s.days,
                    s.joins,
                    leg,  # pyright: ignore[reportArgumentType]
                    min_shift_min=ins.schedule_change_min_shift_min,
                    min_days=ins.schedule_change_min_days,
                )
            )
        out[key] = ItineraryInsights(
            failures=failure_breakdown(
                r.count_insufficient_time, r.count_cancelled, r.count_diverted
            ),
            monthly=_monthly(d, cfg, notes),
            buffer=buffer(
                _operated(d),
                threshold,
                it.median_layover_min,
                ins.buffer_share,
                ins.buffer_round_min,
            ),
            faster_alternatives=faster_alternatives(
                f,
                peers,
                window_min=ins.faster_departure_window_min,
                min_saving_min=ins.faster_min_saving_min,
                margin=ins.faster_margin,
                boot=boot,
            ),
            connecting_options=connecting_options(f, peers, outbound_dep, boot=boot),
            schedule_warnings=schedule_warnings(it.connect_share, legs[0], legs[1]),
            find=find_params(
                it.origin,
                it.dest,
                [it.airline_in, it.airline_out],
                [
                    [(n.flight_number, n.share_of_days) for n in slots[s].slot.flight_numbers]
                    for s in (it.inbound_slot, it.outbound_slot)
                ],
            ),
        )
    return InsightsFile(itineraries=out)
