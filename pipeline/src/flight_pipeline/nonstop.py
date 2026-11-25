"""Typical nonstop time per origin/destination pair (specs/002 research R3, FR-004)."""

from __future__ import annotations

import datetime as dt

import duckdb


def nonstop_medians(
    con: duckdb.DuckDBPyConnection,
    flights: str,
    period: tuple[dt.date, dt.date],
    target: str,
) -> None:
    """Create ``target`` (origin, dest, nonstop_median_min, nonstop_days): the median
    scheduled elapsed time of every nonstop flight-day on the pair, any airline, operated or
    cancelled, over the period. Pairs never flown nonstop are absent."""
    start, end = period
    con.execute(
        f"""
        CREATE OR REPLACE TABLE {target} AS
        WITH days AS (
            SELECT origin, dest, marketing_airline, flight_number, service_date,
                   min(sched_elapsed_min) AS elapsed
            FROM {flights}
            WHERE service_date BETWEEN DATE '{start}' AND DATE '{end}'
            GROUP BY ALL
        )
        SELECT origin, dest,
               CAST(quantile_disc(elapsed, 0.5) AS INTEGER) AS nonstop_median_min,
               CAST(count(*) AS INTEGER) AS nonstop_days
        FROM days
        GROUP BY origin, dest
        ORDER BY origin, dest
        """
    )


def nonstop_ratio(travel_min: int, nonstop_min: int | None) -> float | None:
    """Itinerary travel time over the nonstop time, rounded to 0.1; None without a nonstop."""
    if not nonstop_min:
        return None
    return round(travel_min / nonstop_min + 1e-9, 1)
