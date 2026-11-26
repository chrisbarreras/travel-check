"""Writing the published showcase files (specs/002 contracts/outputs.md, research R5).

The rules every file follows:

- stable bytes: sorted keys, no insignificant whitespace, UTF-8, LF, floats rounded to
  6 decimals, so identical inputs give identical bytes (FR-025);
- validated against its model, with the configuration-dependent rules, when written; any
  failure stops the run (FR-011);
- historical wording only: no text or key may describe a prediction or a passenger outcome
  (FR-014);
- size: the gzip total within ``size_budget_kb`` and ``index.json`` plus ``landing.json``
  within ``landing_budget_kb`` (FR-015, SC-007 proxy), reported per file.
"""

from __future__ import annotations

import gzip
import json
import math
import re
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from flight_pipeline.config import Config, DisruptionNote
from flight_pipeline.showcase.models import (
    NOT_COVERED_KINDS,
    AirlineCoverage,
    Attribution,
    Coverage,
    DataPeriod,
    Definition,
    NotCovered,
    RouteFile,
    ShowcaseIndex,
)

SCHEMA_VERSION = "1.0.0"
FLOAT_DECIMALS = 6

# Phrases that describe a prediction or a passenger outcome rather than a historical
# frequency of feasible schedules (FR-014). Matched case-insensitively on whole words.
FORBIDDEN_WORDING: tuple[str, ...] = (
    "probability",
    "probable",
    "likelihood",
    "likely",
    "chance of",
    "odds",
    "will be feasible",
    "will connect",
    "will make",
    "you will",
    "guaranteed",
    "predict",
    "predicted",
    "prediction",
    "forecast",
    "made the connection",
    "made their connection",
    "missed the connection",
    "missed their connection",
    "passengers made",
    "passengers missed",
    "on-time arrival",
)
_FORBIDDEN = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in FORBIDDEN_WORDING) + r")\b", re.IGNORECASE
)
# A disclaimer that names what the numbers are not is honest wording, not a prediction.
_ALLOWED = re.compile(r"\bnot an? (prediction|forecast)\b", re.IGNORECASE)

_ANCHOR = "docs/methodology.md#"
DEFINITIONS: dict[str, tuple[str, str]] = {
    "connection_feasibility": (
        "Share of the paired days in the data period on which the inbound flight's actual "
        "arrival left at least the minimum connection time plus the boarding cutoff before "
        "the outbound flight's actual departure, with both flights operated. A historical "
        "frequency for the data period, not a prediction.",
        "connection-feasibility",
    ),
    "paired_days": (
        "Days in the data period on which the itinerary's two flights were scheduled to "
        "connect and passed the data-quality checks, including days a leg was cancelled or "
        "diverted (counted as not feasible); the sample behind each rate.",
        "connection-feasibility",
    ),
    "insufficient_data": (
        "Fewer paired days than the minimum sample; no rate is shown, only the count.",
        "connection-feasibility",
    ),
    "slack": (
        "Minutes between the inbound flight's actual arrival and the outbound flight's "
        "actual departure on one paired day. The connection was feasible that day when the "
        "slack was at least the transfer time (minimum connection time) plus the boarding "
        "cutoff and neither leg was cancelled or diverted.",
        "connection-feasibility",
    ),
    "layover": (
        "Scheduled minutes between the inbound arrival and the outbound departure at the "
        "hub, the median over connecting days.",
        "itineraries",
    ),
    "travel_time": (
        "Scheduled minutes from departure at the origin to arrival at the destination, the "
        "median over connecting days.",
        "itineraries",
    ),
    "nonstop_ratio": (
        "Travel time divided by the typical scheduled nonstop time between the same "
        "airports, when a nonstop was flown in the data period.",
        "nonstop-comparison",
    ),
    "comparison_difference": (
        "Difference in connection feasibility between two comparable itineraries on the "
        "same route, in points, with a paired bootstrap interval over the days both were "
        "flown.",
        "comparisons",
    ),
    "settings_compared": (
        "Of the minimum-connection-time and boarding-cutoff settings tested, how many kept "
        "both itineraries comparable with the same order.",
        "sensitivity",
    ),
    "tight_layover": (
        "The scheduled layover is shorter than the minimum connection time plus the "
        "boarding cutoff at the median, or on more than 10% of connecting days; on those "
        "days the connection was feasible only when the inbound was early or the outbound "
        "late.",
        "connection-feasibility",
    ),
    "failure_types": (
        "Days on which the connection was not feasible, by reason: too little time between "
        "operated flights, a cancelled leg, or a diverted leg.",
        "failure-types",
    ),
    "monthly_rate": (
        "Connection feasibility within one calendar month; months below the monthly minimum "
        "sample show the count only.",
        "monthly-view",
    ),
    "buffer": (
        "The scheduled layover that would have left enough time on the configured share of "
        "operated days, rounded up to 5 minutes, shown with the itinerary's median scheduled "
        "layover and the share of operated days on which its scheduled layover was at least "
        "that long.",
        "buffer",
    ),
    "faster_alternative": (
        "A comparable itinerary on the same route with a shorter travel time whose "
        "feasibility, by the paired interval, was no more than the configured margin lower.",
        "faster-alternatives",
    ),
    "connecting_option": (
        "Another outbound flight from the hub that the same inbound flight connected to, "
        "with its own feasibility.",
        "connecting-options",
    ),
    "connect_share": (
        "Share of eligible days on which the two scheduled flights connected within the "
        "layover limits.",
        "itineraries",
    ),
    "schedule_change": (
        "A lasting change in a leg's scheduled departure time within the data period.",
        "schedule-changes",
    ),
    "sold_passengers": (
        "Sampled DB1B passengers on this routing (both airlines, through this hub) in the "
        "data period, shared by the itineraries on the routing.",
        "sold-routings",
    ),
    "disruption_note": (
        "A labelled, sourced event in the data period shown beside the monthly view; never "
        "used in any calculation.",
        "monthly-view",
    ),
}
MEASURES: frozenset[str] = frozenset(DEFINITIONS)

ATTRIBUTION: tuple[Attribution, ...] = (
    Attribution(
        source="BTS",
        text=(
            "Bureau of Transportation Statistics: Airline On-Time Performance, DB1B Market "
            "and T-100 Segment data."
        ),
        licence="US government work, public domain",
        url="https://www.transtats.bts.gov/",
    ),
    Attribution(
        source="airportsdata",
        text=(
            "Airport time zones from the airportsdata package, Copyright (c) 2020- Mike "
            "Borsetti (includes data Copyright (c) 2014 mwgg)."
        ),
        licence="MIT",
        url="https://github.com/mborsetti/airportsdata",
    ),
    Attribution(
        source="tzdata",
        text="Time zone rules from the IANA Time Zone Database, through the tzdata package.",
        licence="IANA data public domain; tzdata package Apache License 2.0",
        url="https://www.iana.org/time-zones",
    ),
)


class PublishError(RuntimeError):
    """A published file failed validation, wording or size checks. Exit code 1."""


# --- Bytes -------------------------------------------------------------------------------


def _round_floats(value: Any) -> Any:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise PublishError(f"non-finite number {value!r} in published data")
        rounded = round(value, FLOAT_DECIMALS)
        return 0.0 if rounded == 0 else rounded
    if isinstance(value, dict):
        return {k: _round_floats(v) for k, v in value.items()}  # pyright: ignore[reportUnknownVariableType]
    if isinstance(value, list):
        return [_round_floats(v) for v in value]  # pyright: ignore[reportUnknownVariableType]
    return value


def stable_bytes(data: BaseModel | Mapping[str, Any]) -> bytes:
    """Compact, sorted, UTF-8 JSON with floats at 6 decimals and a final LF."""
    plain = data.model_dump(mode="json") if isinstance(data, BaseModel) else dict(data)
    text = json.dumps(
        _round_floats(plain), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return (text + "\n").encode("utf-8")


def gzip_size(data: bytes) -> int:
    """Compressed size with a fixed header (mtime 0), so it is reproducible."""
    return len(gzip.compress(data, compresslevel=9, mtime=0))


# --- Checks ------------------------------------------------------------------------------


def wording_violations(data: Any, path: str = "$") -> list[str]:
    """Every text value and key that uses forbidden wording, with its JSON path."""
    found: list[str] = []

    def check(text: str, where: str) -> None:
        cleaned = _ALLOWED.sub("", text)
        m = _FORBIDDEN.search(cleaned.replace("_", " "))
        if m:
            found.append(f"{where}: {m.group(0)!r}")

    if isinstance(data, str):
        check(data, path)
    elif isinstance(data, Mapping):
        for k, v in data.items():  # pyright: ignore[reportUnknownVariableType]
            key = str(k)  # pyright: ignore[reportUnknownArgumentType]
            check(key, f"{path}.{key} (key)")
            found += wording_violations(v, f"{path}.{key}")
    elif isinstance(data, list):
        for i, v in enumerate(data):  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
            found += wording_violations(v, f"{path}[{i}]")
    return found


def size_problems(
    files: Mapping[str, bytes], size_budget_kb: int, landing_budget_kb: int
) -> tuple[dict[str, int], list[str]]:
    """Per-file gzip sizes and any budget exceeded (FR-015)."""
    sizes = {name: gzip_size(b) for name, b in sorted(files.items())}
    total = sum(sizes.values())
    first = sizes.get("index.json", 0) + sizes.get("landing.json", 0)
    problems: list[str] = []
    if total > size_budget_kb * 1024:
        problems.append(
            f"showcase files are {total / 1024:.1f} KB gzip, above the {size_budget_kb} KB budget"
        )
    if first > landing_budget_kb * 1024:
        problems.append(
            f"index.json plus landing.json are {first / 1024:.1f} KB gzip, above the "
            f"{landing_budget_kb} KB landing budget"
        )
    return sizes, problems


def validation_context(cfg: Config) -> dict[str, Any]:
    return {
        "min_sample": cfg.feasibility.min_sample_days,
        "faster_margin": cfg.insights.faster_margin,
        "faster_min_saving_min": cfg.insights.faster_min_saving_min,
    }


def _validated(model: type[BaseModel], data: bytes, context: Mapping[str, Any], name: str) -> None:
    try:
        model.model_validate_json(data, context=dict(context))
    except ValidationError as exc:
        raise PublishError(f"{name} fails validation: {exc}") from exc


# --- Content -----------------------------------------------------------------------------


def definitions() -> list[Definition]:
    return [
        Definition(key=k, text=text, methodology_anchor=_ANCHOR + anchor)
        for k, (text, anchor) in sorted(DEFINITIONS.items())
    ]


def not_covered_texts() -> list[NotCovered]:
    texts = {
        "international": (
            "Itineraries with an international leg: the on-time data covers US domestic "
            "flights only."
        ),
        "two_or_more_stops": "Itineraries with two or more connections.",
        "separate_tickets": (
            "Connections between flights bought as separate tickets, which are not sold "
            "routings in DB1B."
        ),
        "non_reporting_airline": (
            "Flights of airlines that do not report on-time data to BTS, including most "
            "regional partners flying under their own code."
        ),
        "outside_period": "Flights outside the data period.",
        "not_in_showcase": (
            "Routes, hubs and itineraries not listed here: the showcase is a curated "
            "selection, not every connection through the hubs."
        ),
    }
    return [NotCovered(kind=k, text=texts[k]) for k in NOT_COVERED_KINDS]  # pyright: ignore[reportArgumentType]


def coverage(
    routes: Sequence[str],
    hubs: Sequence[str],
    airlines: Sequence[AirlineCoverage],
    period: DataPeriod,
) -> Coverage:
    return Coverage(
        routes=sorted(routes),
        hubs=sorted(hubs),
        airlines=list(airlines),
        period=period,
        not_covered=not_covered_texts(),
    )


def notes_for_route(
    notes: Iterable[DisruptionNote],
    origin: str,
    hub_codes: Iterable[str],
    dest: str,
    airlines: Iterable[str],
) -> list[DisruptionNote]:
    """Notes that name one of the route's airports (origin, hubs, destination) or airlines."""
    airports = {origin, dest, *hub_codes}
    carriers = set(airlines)
    return [n for n in notes if airports & set(n.airports) or carriers & set(n.airlines)]


def landing_file(route: RouteFile, comparison_id: str) -> RouteFile:
    """The landing comparison and its two itineraries, loadable alone."""
    comp = next((c for c in route.comparisons if c.comparison_id == comparison_id), None)
    if comp is None:
        raise PublishError(f"landing comparison {comparison_id} is not in {route.route_id}")
    by_id = {i.itinerary_id: i for i in route.itineraries}
    keep = {comp.itinerary_a, comp.itinerary_b}
    missing = keep - set(by_id)
    if missing:
        raise PublishError(f"landing itineraries {sorted(missing)} are not in the route file")
    its = [i for i in route.itineraries if i.itinerary_id in keep]
    # the route's notes are kept whole: a handful of entries, referenced by the monthly view
    return route.model_copy(update={"itineraries": its, "comparisons": [comp]})


# --- Writing -----------------------------------------------------------------------------


def render(
    index: ShowcaseIndex, routes: Sequence[RouteFile], context: Mapping[str, Any]
) -> dict[str, bytes]:
    """Every published file's bytes, by path relative to the output directory, after
    validation and the wording scan. Raises PublishError on any failure."""
    files: dict[str, bytes] = {}
    by_route = {r.route_id: r for r in routes}
    if index.landing.route_id not in by_route:
        raise PublishError(f"landing route {index.landing.route_id} has no route file")
    listed = {s.route_id for s in index.routes}
    if listed != set(by_route):
        raise PublishError("index routes and route files differ")
    files["index.json"] = stable_bytes(index)
    landing = landing_file(by_route[index.landing.route_id], index.landing.comparison_id)
    files["landing.json"] = stable_bytes(landing)
    for summary in index.routes:
        files[summary.file] = stable_bytes(by_route[summary.route_id])
    problems: list[str] = []
    for name, data in files.items():
        model = ShowcaseIndex if name == "index.json" else RouteFile
        _validated(model, data, context, name)
        problems += [f"{name} {v}" for v in wording_violations(json.loads(data))]
    if problems:
        raise PublishError("forbidden wording: " + "; ".join(problems))
    return files


def write_files(
    out_dir: Path,
    files: Mapping[str, bytes],
    size_budget_kb: int,
    landing_budget_kb: int,
) -> dict[str, int]:
    """Check both budgets, then replace the output directory's JSON files. Returns the
    per-file gzip sizes."""
    sizes, problems = size_problems(files, size_budget_kb, landing_budget_kb)
    if problems:
        report = ", ".join(f"{n} {s / 1024:.1f} KB" for n, s in sizes.items())
        raise PublishError("; ".join(problems) + f" (gzip per file: {report})")
    routes_dir = out_dir / "routes"
    if routes_dir.exists():
        for stale in routes_dir.glob("*.json"):
            stale.unlink()
    for name, data in files.items():
        path = out_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return sizes
