"""Comparability (FR-026), paired bootstrap (research R5), showcase rules and the go
criterion (FR-029, FR-030)."""

from __future__ import annotations

import datetime as dt
import hashlib
from collections.abc import Mapping, Sequence

import duckdb
import numpy as np

from flight_pipeline.config import Itineraries
from flight_pipeline.models import Itinerary


def tight_itineraries(
    itineraries: Sequence[Itinerary], rules: Itineraries, boarding_cutoff: int
) -> set[str]:
    """Itineraries whose median scheduled layover is shorter than their own feasibility
    threshold (minimum connection time for the hub and connection type, plus the boarding
    cutoff): their connection is feasible only when the inbound is early or the outbound late."""
    return {
        i.itinerary_id
        for i in itineraries
        if i.median_layover_min
        < rules.min_connection_for(i.hub, partner=i.partner_connection) + boarding_cutoff
    }


def dep_diff(a: int, b: int) -> int:
    """Difference between two local times of day (minutes), across midnight."""
    d = abs(a - b) % 1440
    return min(d, 1440 - d)


def is_comparable(
    origin_a: str,
    dest_a: str,
    travel_a: int,
    dep_a: int,
    origin_b: str,
    dest_b: str,
    travel_b: int,
    dep_b: int,
    travel_tolerance: int,
    departure_window: int,
) -> bool:
    """Same origin and destination, total scheduled travel times within the tolerance, and
    scheduled departures from the origin within the window (local time of day)."""
    return (
        origin_a == origin_b
        and dest_a == dest_b
        and abs(travel_a - travel_b) <= travel_tolerance
        and dep_diff(dep_a, dep_b) <= departure_window
    )


def comparable_candidates(
    con: duckdb.DuckDBPyConnection,
    itineraries: str,
    travel_tolerance: int,
    departure_window: int,
    target: str,
) -> None:
    """Create ``target`` (itinerary_x < itinerary_y, origin, dest, hub_x, hub_y,
    travel_diff_min, dep_diff_min): every comparable pair of distinct itineraries."""
    con.execute(
        f"""
        CREATE OR REPLACE TABLE {target} AS
        WITH p AS (
            SELECT x.itinerary_id AS itinerary_x, y.itinerary_id AS itinerary_y,
                   x.origin, x.dest, x.hub AS hub_x, y.hub AS hub_y,
                   CAST(abs(x.median_travel_min - y.median_travel_min) AS INTEGER)
                       AS travel_diff_min,
                   CAST(abs(x.median_dep_local_min - y.median_dep_local_min) % 1440 AS INTEGER)
                       AS raw_dep
            FROM {itineraries} x
            JOIN {itineraries} y
              ON x.origin = y.origin AND x.dest = y.dest AND x.itinerary_id < y.itinerary_id
        )
        SELECT itinerary_x, itinerary_y, origin, dest, hub_x, hub_y, travel_diff_min,
               CAST(least(raw_dep, 1440 - raw_dep) AS INTEGER) AS dep_diff_min
        FROM p
        WHERE travel_diff_min <= {int(travel_tolerance)}
          AND least(raw_dep, 1440 - raw_dep) <= {int(departure_window)}
        ORDER BY itinerary_x, itinerary_y
        """
    )


# --- Paired bootstrap (research R5) ------------------------------------------------------


def _stable_int(key: str) -> int:
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big")


def paired_bootstrap(
    a: Mapping[dt.date, bool],
    b: Mapping[dt.date, bool],
    resamples: int,
    ci_level: float,
    seed: int,
    key: str,
) -> tuple[float | None, float | None]:
    """Confidence interval for rate(a) - rate(b), resampling whole service dates.

    Dates are the union of dates on which either itinerary has a paired outcome
    (``True`` = feasible). Each resample draws that many dates with replacement; each
    itinerary's rate is computed on the drawn dates where it has an outcome. Resampling
    dates keeps the correlation between two itineraries flying on the same day. The random
    stream is seeded from ``seed`` and ``key`` (the pair), so results are reproducible and
    independent across pairs."""
    days = sorted(set(a) | set(b))
    if not a or not b or not days:
        return None, None
    has_a = np.array([d in a for d in days])
    has_b = np.array([d in b for d in days])
    feas_a = np.array([a.get(d, False) for d in days])
    feas_b = np.array([b.get(d, False) for d in days])
    rng = np.random.default_rng(np.random.SeedSequence([seed, _stable_int(key)]))
    idx = rng.integers(0, len(days), size=(resamples, len(days)))
    with np.errstate(invalid="ignore", divide="ignore"):
        rate_a = feas_a[idx].sum(axis=1) / has_a[idx].sum(axis=1)
        rate_b = feas_b[idx].sum(axis=1) / has_b[idx].sum(axis=1)
    diffs = rate_a - rate_b
    diffs = diffs[~np.isnan(diffs)]
    if diffs.size == 0:
        return None, None
    alpha = 1.0 - ci_level
    low, high = np.percentile(diffs, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return round(float(low), 6), round(float(high), 6)


# --- Showcase rules and go criterion (FR-029, FR-030) ------------------------------------


def shared_days(a: Mapping[dt.date, bool], b: Mapping[dt.date, bool]) -> int:
    """Number of dates on which both itineraries have a paired outcome."""
    return len(set(a) & set(b))


def order_pair(x: str, y: str, rate_x: float | None, rate_y: float | None) -> tuple[str, str]:
    """``itinerary_a`` has the higher default rate; ties or a missing rate: smaller id first."""
    if rate_x is None or rate_y is None or rate_x == rate_y:
        return (x, y) if x < y else (y, x)
    return (x, y) if rate_x > rate_y else (y, x)


def is_showcase(
    *,
    rate_a: float | None,
    rate_b: float | None,
    sufficient_a: bool,
    sufficient_b: bool,
    ci_low: float | None,
    ci_high: float | None,
    assumption_sensitive: bool,
    gap: float,
    shared_days: int,
    min_shared_days: int,
) -> bool:
    """Both sufficient, observed on at least ``min_shared_days`` of the same dates (so they
    are real alternatives and the interval is paired), not assumption-sensitive, a gap of
    at least ``gap`` and a confidence interval for the difference that excludes zero."""
    if not (sufficient_a and sufficient_b) or rate_a is None or rate_b is None:
        return False
    if shared_days < min_shared_days:
        return False
    if ci_low is None or ci_high is None or assumption_sensitive:
        return False
    if round(rate_a - rate_b, 6) < round(gap, 6):
        return False
    return ci_low > 0 or ci_high < 0


def go_criteria(
    example_hubs: Sequence[tuple[str, str]], min_examples: int, min_hubs: int
) -> tuple[bool, bool]:
    """(at least ``min_examples`` showcase examples, examples spread across at least
    ``min_hubs`` different hubs). An example's hubs are those of its two itineraries."""
    hubs = {h for pair in example_hubs for h in pair}
    return len(example_hubs) >= min_examples, len(hubs) >= min_hubs
