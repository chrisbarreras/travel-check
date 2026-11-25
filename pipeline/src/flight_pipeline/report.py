"""Summary report sections, summary.json/summary.md and the run manifest.

Reporting rules (contracts/outputs.md): every rate is shown with its sample size and data
period; itineraries below the minimum sample show "insufficient data" and no rate; wording is
"connection feasibility", never passenger-outcome language (FR-032).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from collections.abc import Set as AbstractSet
from typing import Any

from flight_pipeline.config import HubWeights
from flight_pipeline.models import (
    AirlineCoverage,
    ComparablePair,
    Finding,
    HubCandidate,
    HubSelection,
    Itinerary,
    ItineraryResult,
    OdExclusions,
    OdSelection,
    ShowcaseBreakdown,
)

_REASON_TEXT = {
    "score": "score",
    "weather_winter": "winter weather peak",
    "weather_summer": "summer weather peak",
    "weather_above_median": "weather share above the pool median",
    "weather_below_median": "weather share below the pool median",
}


def reason_text(reason: str) -> str:
    if reason.startswith("airline_coverage:"):
        return f"airline coverage: {reason.split(':', 1)[1]}"
    return _REASON_TEXT.get(reason, reason)


def pct(value: float | None, digits: int = 0) -> str:
    return "n/a" if value is None else f"{value * 100:.{digits}f}%"


def table(header: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def hub_section(
    candidates: Sequence[HubCandidate],
    selection: Sequence[HubSelection],
    unmet: Sequence[str],
    median_weather_share: float,
    *,
    weights: HubWeights | None = None,
) -> str:
    """FR-012: every candidate's metrics, score, eligibility and rank; the selected hubs and
    why each was selected; every unmet constraint."""
    sel = {s.airport: s for s in selection}
    rows: list[list[object]] = []
    for c in sorted(candidates, key=lambda c: c.rank):
        s = sel[c.airport]
        rows.append(
            [
                c.rank,
                c.airport,
                f"{c.score:.3f}",
                f"{'yes' if c.eligible else 'no'} ({c.eligible_itineraries})",
                f"{c.departures:,}",
                ", ".join(c.airlines) or "none",
                "missing (scored as 0)" if c.passengers is None else f"{c.passengers:,}",
                pct(c.weather_share, 1),
                " / ".join(
                    pct(getattr(c.weather_share_by_season, s), 1)
                    for s in ("winter", "spring", "summer", "autumn")
                ),
                c.weather_peak_season,
                f"selected ({reason_text(s.reason)})" if s.selected and s.reason else "",
            ]
        )
    unmet_text = "none" if not unmet else "; ".join(unmet)
    return "\n\n".join(
        [
            "## Hub selection",
            "Candidates are the airports with the most scheduled departures. Score = "
            + _weights_text(weights)
            + " airline count, scheduled departures and passengers boarded, each scaled "
            "to 0-1 across the candidates. Eligible = at least the configured number of "
            "qualifying itineraries from origins outside the candidate pool (number in "
            "brackets). Weather share = share of scheduled departures with weather-attributed "
            "delay or a weather cancellation; the pool median is "
            f"{pct(median_weather_share, 1)}.",
            table(
                [
                    "Rank",
                    "Airport",
                    "Score",
                    "Eligible (itineraries)",
                    "Departures",
                    "Airlines (>= share)",
                    "Passengers",
                    "Weather share",
                    "Weather by season (W / Sp / Su / Au)",
                    "Weather peak",
                    "Selection",
                ],
                rows,
            ),
            f"**Unmet constraints:** {unmet_text}",
        ]
    )


def _weights_text(weights: HubWeights | None) -> str:
    if weights is None or weights.airlines == weights.departures == weights.passengers:
        return "equally weighted"
    return (
        f"weights {weights.airlines:g} (airlines), {weights.departures:g} (departures), "
        f"{weights.passengers:g} (passengers) on"
    )


def airline_coverage(
    itinerary_airlines: Sequence[str], sold_same_airline: Mapping[str, int]
) -> list[AirlineCoverage]:
    """Per marketing airline: itineraries (by inbound airline) and sampled passengers on sold
    same-airline routings, sorted by passengers, then airline."""
    counts: dict[str, int] = {}
    for a in itinerary_airlines:
        counts[a] = counts.get(a, 0) + 1
    airlines = set(counts) | set(sold_same_airline)
    rows = [
        AirlineCoverage(
            airline=a, itineraries=counts.get(a, 0), sold_passengers=sold_same_airline.get(a, 0)
        )
        for a in airlines
    ]
    return sorted(rows, key=lambda r: (-r.sold_passengers, -r.itineraries, r.airline))


def airline_section(rows: Sequence[AirlineCoverage], *, recurrence_threshold: float) -> str:
    """Which airlines the itineraries come from, against what each sells through the hubs."""
    missing = [r.airline for r in rows if r.itineraries == 0 and r.sold_passengers > 0]
    return "\n\n".join(
        [
            "## Airlines covered",
            "Itineraries through the selected hubs by marketing airline (inbound flight), "
            "next to the sampled DB1B passengers on sold routings through the same hubs with "
            "one airline on both legs.",
            table(
                ["Airline", "Itineraries", "Sold passengers, same-airline routings"],
                [[r.airline, f"{r.itineraries:,}", f"{r.sold_passengers:,}"] for r in rows],
            ),
            "**No itineraries:** "
            + (", ".join(missing) if missing else "none")
            + ". An itinerary is identified by flight number, and each flight must be "
            f"scheduled on at least {round(recurrence_threshold * 100)}% of days, so an airline "
            "that reassigns flight numbers often (Southwest does) can sell many connections "
            "without any qualifying itinerary.",
        ]
    )


def od_section(
    rows: Sequence[OdSelection],
    itinerary_counts: dict[tuple[str, str], int],
    shortfalls: Sequence[str],
    without_itineraries: Sequence[str],
) -> str:
    """Selected origin/destination pairs with rank and comparable-pair count (FR-025), and
    pairs with no qualifying itineraries (FR-018)."""
    chosen = [r for r in rows if r.selected]
    body = table(
        ["Rank", "Pair", "Regional origin", "Main hub", "Comparable pairs", "Itineraries"],
        [
            [
                r.rank,
                f"{r.origin}-{r.dest}",
                "yes" if r.regional_origin else "no",
                r.main_hub,
                r.comparable_pairs,
                itinerary_counts.get((r.origin, r.dest), 0),
            ]
            for r in sorted(chosen, key=lambda r: r.rank)
        ],
    )
    regional = sum(r.regional_origin for r in chosen)
    not_selected = len(rows) - len(chosen)
    parts = [
        "## Origin/destination pairs",
        "Pairs are chosen from the data: candidates have at least two qualifying itineraries "
        "through the selected hubs and are ranked by their number of comparable itinerary "
        "pairs (same origin and destination, scheduled travel time and departure time close "
        "together).",
        body,
        f"{regional} of {len(chosen)} selected pairs have a regional origin.",
        f"**Not selected:** {not_selected} other candidate pairs.",
        "**Selection shortfalls:** " + ("; ".join(shortfalls) if shortfalls else "none"),
        "**Pairs without qualifying itineraries:** "
        + (", ".join(without_itineraries) if without_itineraries else "none"),
    ]
    return "\n\n".join(parts)


def exclusions_section(
    rows: Sequence[OdExclusions], *, min_sold_passengers: int, recurrence_threshold: float
) -> str:
    """FR-018a: candidates removed by each itinerary rule, in order, per selected pair."""
    body = table(
        [
            "Pair",
            "Candidates",
            "Times can never connect",
            "Routing not sold",
            "Never connect within the layover limits",
            "Connect on too few days",
            "Qualifying",
        ],
        [
            [
                f"{r.origin}-{r.dest}",
                r.candidates,
                r.excluded_bounds,
                r.excluded_unsold,
                r.excluded_not_connecting,
                r.excluded_recurrence,
                r.qualifying,
            ]
            for r in sorted(rows, key=lambda r: (r.origin, r.dest))
        ],
    )
    return "\n\n".join(
        [
            "## Itinerary rules applied",
            "For each selected pair, candidates are pairs of regular schedules (an airline's "
            "flights on a route at about the same time of day, whatever their flight numbers) "
            "through a selected hub, sold by the same airline or a partner pair, each "
            "scheduled on most days. The rules then remove, in order: pairs whose times can "
            "never give a layover within the limits; a routing not sold, meaning DB1B does not "
            f"show at least {min_sold_passengers} sampled passengers on that routing and pair "
            "of selling airlines over the period; pairs whose flights never connect within the "
            "layover limits on any day; and flights that connect on fewer than "
            f"{round(recurrence_threshold * 100)}% of days in the period.",
            body,
        ]
    )


def rate_text(r: ItineraryResult) -> str:
    if r.status == "insufficient_data" or r.feasibility_rate is None:
        return f"insufficient data ({r.paired_days} days)"
    return f"{pct(r.feasibility_rate)} ({r.count_feasible} of {r.paired_days} days)"


def results_section(
    results: Sequence[ItineraryResult], hub_of: dict[str, str], min_sample_days: int
) -> str:
    """Default-scenario connection feasibility per itinerary (FR-023, FR-024)."""
    if not results:
        return "## Connection feasibility\n\nNo itineraries were evaluated."
    period = f"{results[0].period_start} to {results[0].period_end}"
    rows = [
        [
            r.itinerary_id,
            hub_of.get(r.itinerary_id, ""),
            rate_text(r),
            r.count_insufficient_time,
            r.count_cancelled,
            r.count_diverted,
            "n/a"
            if r.slack_p50 is None
            else f"{r.slack_min} / {r.slack_p10} / {r.slack_p50} / {r.slack_p90}",
            f"{r.excluded_not_connecting} / {r.excluded_quality}",
        ]
        for r in sorted(results, key=lambda r: r.itinerary_id)
    ]
    return "\n\n".join(
        [
            "## Connection feasibility",
            f"Data period: {period}. Connection feasibility is the share of paired days on "
            "which the scheduled connection would have been possible: the outbound flight's "
            "actual gate departure was at least the boarding cutoff plus the minimum "
            "connection time after the inbound flight's actual gate arrival. It is a "
            "historical frequency, not a prediction, and it does not describe what happened "
            "to any traveler. Cancellations and diversions are counted as failures and shown "
            f"separately. Itineraries with fewer than {min_sample_days} paired days show "
            '"insufficient data" instead of a rate.',
            table(
                [
                    "Itinerary",
                    "Hub",
                    "Connection feasibility",
                    "Insufficient time",
                    "Cancelled",
                    "Diverted",
                    "Slack min / p10 / p50 / p90 (minutes)",
                    "Excluded days: not connecting / data quality",
                ],
                rows,
            ),
        ]
    )


# --- Sensitivity, showcases and the finding ----------------------------------------------

LIMITATIONS = (
    "Airlines sometimes hold an outbound flight for connecting passengers. The data cannot "
    "show this, so some days classified as insufficient time may have worked in practice.",
    "Gate changes and the walking distance between gates are not in the data.",
    "How full flights were is not considered: a feasible connection does not mean a seat was "
    "available.",
    "Transfer time is assumed (the hub's minimum connection time), not measured.",
    "Results are historical frequencies for the data period, not a prediction of future "
    "connection feasibility.",
    "Weather is measured only through BTS weather-attributed delays and weather "
    "cancellations; weather recorded under National Aviation System delays is not counted.",
    "Many comparisons are made, each at the stated confidence level, with no "
    "multiple-comparison correction, so a single example can be a chance result; the "
    "decision rests on the number and spread of examples.",
    "Sold routings come from DB1B, a 10% ticket sample: a routing sold rarely may have fewer "
    "sampled passengers than the minimum and be left out. DB1B records the selling airline, "
    "not the flight numbers, so a sold routing qualifies every flight pair on it that meets "
    "the other rules.",
    "Itineraries are identified by flight number. Airlines that reassign flight numbers "
    "often, such as Southwest, have few flights scheduled on most days under one number, so "
    "their connections are largely missing; the report lists itineraries per airline.",
)

CI_METHOD = (
    "Paired day-level bootstrap: the service dates on which either itinerary has a paired "
    "outcome are resampled with replacement (10,000 times by default, fixed seed); each "
    "itinerary's feasibility rate is computed on the drawn dates where it has an outcome, "
    "and the interval is the central percentile range of the differences. A showcase also "
    "needs both itineraries observed on at least the minimum sample size of the same dates. "
    "Resampling whole "
    "dates keeps the correlation between itineraries flying on the same day (shared weather "
    "and congestion), as FR-029 requires."
)

ATTRIBUTION = (
    "Flight data: U.S. Department of Transportation, Bureau of Transportation Statistics "
    "(TranStats): Marketing Carrier On-Time Performance, T-100 Domestic Segment (U.S. "
    "Carriers) and the Airline Origin and Destination Survey (DB1B Market). Airport time "
    "zones: airportsdata (MIT License, Copyright (c) 2020- Mike Borsetti; includes data "
    "Copyright (c) 2014 mwgg). Time-zone rules: tzdata (Apache License 2.0)."
)


def hub_of_id(itinerary_id: str) -> str:
    """Hub code from an itinerary id ``{origin}-{hub}-{dest}:...``."""
    return itinerary_id.split(":", 1)[0].split("-")[1]


def points(value: float) -> str:
    return f"{value * 100:+.0f}"


def sensitivity_section(
    rows: Sequence[Mapping[str, Any]],
    sensitive_pairs: Sequence[ComparablePair],
    pair_scenarios_not_comparable: int,
) -> str:
    """FR-027/FR-028: results under every scenario and the assumption-sensitive pairs."""
    body = table(
        [
            "Scenario",
            "Min. connection (min)",
            "Boarding cutoff (min)",
            "Recurrence",
            "Itineraries",
            "Sufficient data",
            "Median connection feasibility",
            "Comparable pairs reversed",
        ],
        [
            [
                f"{r['scenario_id']} (default)" if r["is_default"] else r["scenario_id"],
                r["min_connection_min"],
                r["boarding_cutoff_min"],
                f"{round(r['recurrence_threshold'] * 100)}%",
                r["itineraries"],
                r["sufficient"],
                pct(r["median_rate"]),
                r["reversals"],
            ]
            for r in rows
        ],
    )
    listed = (
        ", ".join(f"{p.itinerary_a} vs {p.itinerary_b}" for p in sensitive_pairs)
        if sensitive_pairs
        else "none"
    )
    return "\n\n".join(
        [
            "## Sensitivity to assumptions",
            "Every analyzed itinerary is re-evaluated under each combination of minimum "
            "connection time, boarding cutoff and recurrence threshold, with the hub and "
            "origin/destination pair selection fixed. A comparable pair is "
            "assumption-sensitive when its order by connection feasibility reverses in any "
            "scenario.",
            body,
            f"**Assumption-sensitive pairs:** {listed}",
            f"{pair_scenarios_not_comparable} pair-scenario combinations could not be "
            "compared because an itinerary did not qualify or had insufficient data in that "
            "scenario; they are not counted as reversals.",
        ]
    )


def _od_of(itinerary_id: str) -> str:
    origin, _, dest = itinerary_id.split(":", 1)[0].split("-")
    return f"{origin}-{dest}"


def showcase_section(
    examples: Sequence[ComparablePair],
    results: Mapping[str, ItineraryResult],
    hub_of: Mapping[str, str],
    ci_level: float,
    *,
    layover: Mapping[str, int] | None = None,
    tight: AbstractSet[str] = frozenset(),
    total_settings: int = 9,
    sold: Mapping[str, int] | None = None,
    missing_settings: Mapping[tuple[str, str], str] | None = None,
    routing_itineraries: Mapping[str, int] | None = None,
) -> str:
    """The strongest showcase example per origin/destination pair (largest difference),
    with the total count; every example is listed in summary.json. Discloses at how many
    (minimum connection time, boarding cutoff) settings each example was compared (FR-027,
    FR-028), each itinerary's sampled DB1B passengers, and which itineraries are scheduled
    tighter than their own feasibility threshold."""
    layover = layover or {}
    sold = sold or {}
    missing_settings = missing_settings or {}
    sharing = routing_itineraries or {}

    def sold_text(i: str) -> str:
        if i not in sold:
            return "n/a"
        n = sharing.get(i)
        return f"{sold[i]}" if n is None else f"{sold[i]} on {n} itineraries"

    def settings_text(p: ComparablePair) -> str:
        note = missing_settings.get((p.itinerary_a, p.itinerary_b), "")
        return f"{p.settings_compared} of {total_settings}" + (f" ({note})" if note else "")

    level = f"{round(ci_level * 100)}%"
    if not examples:
        return "## Showcase examples\n\nNo pair of comparable itineraries met every condition."
    best: dict[str, ComparablePair] = {}
    for p in examples:
        od = _od_of(p.itinerary_a)
        current = best.get(od)
        key = (p.rate_diff or 0.0, p.itinerary_b)
        if current is None or key > (current.rate_diff or 0.0, current.itinerary_b):
            best[od] = p
    hubs = {hub_of.get(i, hub_of_id(i)) for p in examples for i in (p.itinerary_a, p.itinerary_b)}
    rows: list[list[object]] = []
    for od, p in sorted(best.items(), key=lambda kv: (-(kv[1].rate_diff or 0.0), kv[0])):
        ra, rb = results[p.itinerary_a], results[p.itinerary_b]
        diff = (
            "n/a"
            if p.rate_diff is None or p.ci_low is None or p.ci_high is None
            else f"{points(p.rate_diff)} points ({level} CI {points(p.ci_low)} to "
            f"{points(p.ci_high)})"
        )
        rows.append(
            [
                od,
                f"{p.itinerary_a} ({hub_of.get(p.itinerary_a, '')})",
                rate_text(ra),
                f"{p.itinerary_b} ({hub_of.get(p.itinerary_b, '')})",
                rate_text(rb),
                diff,
                f"{layover.get(p.itinerary_a, 'n/a')} / {layover.get(p.itinerary_b, 'n/a')}"
                + (" (tighter than threshold)" if p.itinerary_b in tight else ""),
                f"{sold_text(p.itinerary_a)} / {sold_text(p.itinerary_b)}",
                settings_text(p),
                p.shared_days,
                f"travel time within {p.travel_diff_min} min, departure within "
                f"{p.dep_diff_min} min",
            ]
        )
    in_all = sum(p.settings_compared >= total_settings for p in examples)
    fewest = min(p.settings_compared for p in examples)
    tight_lower = sum(p.itinerary_b in tight for p in examples)
    notes: dict[str, int] = {}
    for p in examples:
        note = missing_settings.get((p.itinerary_a, p.itinerary_b), "")
        if note:
            notes[note] = notes.get(note, 0) + 1
    missing_text = (
        " Of the others: "
        + "; ".join(f"{n} {note}" for note, n in sorted(notes.items(), key=lambda kv: -kv[1]))
        + "."
        if notes
        else ""
    )
    return "\n\n".join(
        [
            "## Showcase examples",
            "Pairs of comparable itineraries, both with sufficient data and not "
            "assumption-sensitive, whose connection feasibility differs by at least the "
            f"showcase threshold with a {level} confidence interval that excludes zero.",
            f"{len(examples)} showcase examples in {len(best)} origin/destination pairs, "
            f"across {len(hubs)} hubs. The strongest example per pair is shown; every "
            "example is listed in summary.json.",
            f"{in_all} of {len(examples)} examples were compared at all {total_settings} "
            f"settings of minimum connection time and boarding cutoff (fewest: {fewest}); at "
            "the remaining settings an itinerary did not qualify or had insufficient data, so "
            "the order could not be checked there. Connection feasibility depends only on "
            "these two settings; the recurrence threshold changes which itineraries qualify."
            + missing_text,
            f"In {tight_lower} of {len(examples)} examples the lower itinerary's scheduled "
            "layover is shorter than its feasibility threshold (minimum connection time plus "
            "boarding cutoff): its connection is feasible only on days when the inbound flight "
            "arrives early or the outbound leaves late.",
            table(
                [
                    "Pair",
                    "Itinerary A",
                    "Connection feasibility A",
                    "Itinerary B",
                    "Connection feasibility B",
                    "Difference",
                    "Scheduled layover A / B (min)",
                    "Sold passengers on routing A / B (DB1B sample; shared by its itineraries)",
                    "Settings compared",
                    "Shared dates",
                    "Comparability",
                ],
                rows,
            ),
        ]
    )


def routing_itineraries(itineraries: Sequence[Itinerary]) -> dict[str, int]:
    """For each itinerary, how many qualifying itineraries share its sold routing (origin,
    hub, destination and the two selling airlines). DB1B passengers are counted per routing,
    so they are shared by all of these itineraries."""

    def key(i: Itinerary) -> tuple[str, str, str, str, str]:
        return (i.origin, i.hub, i.dest, i.airline_in, i.airline_out)

    counts: dict[tuple[str, str, str, str, str], int] = {}
    for i in itineraries:
        counts[key(i)] = counts.get(key(i), 0) + 1
    return {i.itinerary_id: counts[key(i)] for i in itineraries}


def describe_missing_settings(
    missing: Sequence[tuple[int, int]], mcts: Sequence[int], cutoffs: Sequence[int]
) -> str:
    """Settings (minimum connection time, cutoff) at which a pair was not compared, in words.
    Empty when none are missing; whole minimum-connection values are named once."""
    if not missing:
        return ""
    gone = set(missing)
    whole = [m for m in sorted(mcts) if all((m, c) in gone for c in cutoffs)]
    rest = sorted(x for x in gone if x[0] not in whole)
    parts: list[str] = []
    if whole:
        parts.append("minimum connection " + ", ".join(str(m) for m in whole) + " min")
    if rest:
        parts.append("minimum connection / cutoff " + ", ".join(f"{m}/{c}" for m, c in rest))
    return "not at " + "; ".join(parts)


NONSTOP_RATIO_LIMIT = 1.5


def showcase_breakdown(
    examples: Sequence[ComparablePair],
    itineraries: Mapping[str, Itinerary],
    *,
    tight: AbstractSet[str],
    nonstop_min: Mapping[tuple[str, str], int],
    missing_settings: Mapping[tuple[str, str], str] | None = None,
    ratio_limit: float = NONSTOP_RATIO_LIMIT,
) -> ShowcaseBreakdown:
    """Counts the go/no-go decision cites, so they are produced and verified by the pipeline
    (SC-010): examples per pair, cross-hub examples, the subset whose lower itinerary is not
    scheduled tighter than its threshold, and travel time against the median nonstop."""
    missing_settings = missing_settings or {}
    per_pair: dict[str, int] = {}
    for p in examples:
        per_pair[_od_of(p.itinerary_a)] = per_pair.get(_od_of(p.itinerary_a), 0) + 1
    cross = sum(itineraries[p.itinerary_a].hub != itineraries[p.itinerary_b].hub for p in examples)
    clean = [p for p in examples if p.itinerary_b not in tight]
    clean_hubs = sorted({itineraries[i].hub for p in clean for i in (p.itinerary_a, p.itinerary_b)})
    slower = without = 0
    worst: float | None = None
    for p in examples:
        a = itineraries[p.itinerary_a]
        nonstop = nonstop_min.get((a.origin, a.dest))
        if not nonstop:
            without += 1
            continue
        travel = max(a.median_travel_min, itineraries[p.itinerary_b].median_travel_min)
        r = round(travel / nonstop, 6)
        slower += r > ratio_limit
        worst = r if worst is None else max(worst, r)
    notes: dict[str, int] = {}
    for p in examples:
        note = missing_settings.get((p.itinerary_a, p.itinerary_b), "")
        if note:
            notes[note] = notes.get(note, 0) + 1
    return ShowcaseBreakdown(
        examples=len(examples),
        examples_per_pair=dict(sorted(per_pair.items(), key=lambda kv: (-kv[1], kv[0]))),
        cross_hub_examples=cross,
        examples_without_tight_layover=len(clean),
        pairs_without_tight_layover=len({_od_of(p.itinerary_a) for p in clean}),
        hubs_without_tight_layover=clean_hubs,
        nonstop_ratio_limit=ratio_limit,
        examples_slower_than_ratio=slower,
        examples_without_nonstop=without,
        max_nonstop_ratio=worst,
        examples_missing_settings=notes,
    )


def breakdown_section(b: ShowcaseBreakdown) -> str:
    """The showcase subsets the go/no-go decision relies on (SC-010)."""
    worst = "n/a" if b.max_nonstop_ratio is None else f"{b.max_nonstop_ratio:.1f}"
    plural = "example has" if b.examples_without_nonstop == 1 else "examples have"
    return "\n\n".join(
        [
            "## Breakdown of the showcase examples",
            table(["Pair", "Showcase examples"], [[k, v] for k, v in b.examples_per_pair.items()]),
            f"{b.cross_hub_examples} of {b.examples} examples compare itineraries through "
            "different hubs; the rest compare flights through the same hub.",
            "Without the examples whose lower itinerary is scheduled tighter than its "
            f"feasibility threshold, {b.examples_without_tight_layover} examples, in "
            f"{b.pairs_without_tight_layover} pairs and across "
            f"{len(b.hubs_without_tight_layover)} hubs "
            f"({', '.join(b.hubs_without_tight_layover)}), remain.",
            f"In {b.examples_slower_than_ratio} of {b.examples} examples the slower itinerary "
            f"takes more than {b.nonstop_ratio_limit:g} times the median scheduled nonstop "
            f"time on the same pair (at most {worst} times). These routings are sold, so they "
            f"stay in. {b.examples_without_nonstop} {plural} no nonstop to compare with.",
        ]
    )


def finding_json(finding: Finding) -> str:
    return json.dumps(finding.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def render_summary(
    finding: Finding,
    sections: Sequence[str],
    min_examples: int = 3,
    min_hubs: int = 2,
    appendix: Sequence[str] = (),
) -> str:
    example_hubs = {
        hub_of_id(i) for p in finding.showcase_examples for i in (p.itinerary_a, p.itinerary_b)
    }
    decision = {"go": "GO", "no_go": "NO-GO", "pivot": "PIVOT"}[finding.decision]
    criteria = table(
        ["Criterion", "Observed", "Result"],
        [
            [
                f"At least {min_examples} showcase examples",
                len(finding.showcase_examples),
                "met" if finding.criterion_min_examples_met else "not met",
            ],
            [
                f"Examples across at least {min_hubs} hubs",
                len(example_hubs),
                "met" if finding.criterion_min_hubs_met else "not met",
            ],
        ],
    )
    failures = {"cancelled", "diverted"}
    dq = sorted(finding.data_quality.items())
    excluded = ", ".join(f"{k}: {v:,}" for k, v in dq if k not in failures) or "none"
    kept = ", ".join(f"{k}: {v:,}" for k, v in dq if k in failures) or "none"
    parts = [
        "# Phase 0 finding: connection feasibility experiment",
        f"Data period: {finding.ontime_period_start} to {finding.ontime_period_end} for every "
        "source: on-time flights, T-100 passengers and DB1B sold routings (DB1B quarters "
        + (
            f"{finding.db1b_quarters[0]} to {finding.db1b_quarters[-1]}"
            if finding.db1b_quarters
            else "none"
        )
        + ").",
        "Sold routings come from DB1B, a 10% sample of airline tickets. "
        f"{pct(finding.db1b_unknown_airline_share, 1)} of the sampled one-connection "
        "passengers had a leg with no recorded selling airline and were not counted. "
        + (
            f"{pct(finding.db1b_unmapped_airline_share, 1)} of the sampled one-connection "
            "passengers were on routings sold by an airline that is neither a marketing "
            "airline in the on-time data nor mapped in configuration ("
            + ", ".join(f"{k} {v:,}" for k, v in finding.db1b_unmapped_airlines.items())
            + "); those routings can never match an itinerary. "
            if finding.db1b_unmapped_airlines
            else "Every selling airline in DB1B is a marketing airline in the on-time data. "
        )
        + "DB1B fares are not used.",
        f"**Decision: {decision}**",
        "## Go/no-go criteria",
        criteria,
        *sections,
        "## Confidence interval method",
        finding.ci_method,
        "## Known limitations",
        "\n".join(f"- {item}" for item in finding.limitations),
        "## Data quality",
        f"Excluded from every sample: {excluded}. Kept and counted as failures: {kept}. "
        "Counts by month are in quality.json.",
        *appendix,
        "## Attribution",
        ATTRIBUTION,
    ]
    return "\n\n".join(parts) + "\n"
