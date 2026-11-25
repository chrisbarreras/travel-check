"""Daily connection outcomes and per-itinerary results (FR-019 to FR-024, ADR-0005).

For each itinerary and each in-period day its inbound flight was scheduled:

1. The outbound instance is the earliest one of the outbound pattern scheduled to leave
   within [minimum connection, maximum layover] after that day's inbound scheduled arrival
   (so a next-day outbound is matched correctly). No such instance: the day is excluded as
   ``not_connecting``.
2. If either leg failed a data-quality check, the day is excluded as ``quality``.
3. Otherwise the day is paired and classified (data-model.md DailyOutcome state rule):
   cancelled (either leg) -> diverted (either leg) -> feasible when
   raw slack >= boarding cutoff + minimum connection time -> insufficient time.

Raw slack = outbound actual gate departure - inbound actual gate arrival, from UTC instants,
for the same connection day only; per-leg delay distributions are never combined.
"""

from __future__ import annotations

import datetime as dt
import math
from collections.abc import Sequence

import duckdb

from flight_pipeline.config import Itineraries

PERCENTILES = {"slack_p10": 0.1, "slack_p50": 0.5, "slack_p90": 0.9}


def lower_percentile(values: Sequence[int], q: float) -> int | None:
    """Discrete "lower" percentile: sorted ascending, the value at index floor(q * (n - 1))."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[math.floor(q * (len(ordered) - 1))]


def _instances(con: duckdb.DuckDBPyConnection, flights: str) -> None:
    """One row per flight instance. Identical duplicate copies are dropped; an instance with
    no ``ok`` row (conflicting copies, missing times, clock mismatch) has ``ok_n = 0``."""
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _inst AS
        SELECT marketing_airline, flight_number, origin, dest, service_date,
               count(*) FILTER (WHERE quality_flag = 'ok') AS ok_n,
               min(sched_dep_utc) AS sched_dep,
               min(sched_arr_utc) AS sched_arr,
               any_value(actual_dep_utc) FILTER (WHERE quality_flag = 'ok') AS actual_dep,
               any_value(actual_arr_utc) FILTER (WHERE quality_flag = 'ok') AS actual_arr,
               coalesce(bool_or(cancelled) FILTER (WHERE quality_flag = 'ok'), false)
                   AS cancelled,
               coalesce(bool_or(diverted) FILTER (WHERE quality_flag = 'ok'), false)
                   AS diverted
        FROM {flights}
        WHERE quality_flag <> 'duplicate'
        GROUP BY ALL
        """
    )


def daily_slack(
    con: duckdb.DuckDBPyConnection,
    flights: str,
    itineraries: str,
    rules: Itineraries,
    period: tuple[dt.date, dt.date],
    target: str,
) -> None:
    """Create ``target`` (itinerary_id, service_date, status, min_connection_min,
    any_cancelled, any_diverted, raw_slack_min): one row per in-period inbound day."""
    _instances(con, flights)
    con.execute("CREATE OR REPLACE TEMP TABLE _it_rules (itinerary_id VARCHAR, min_conn INTEGER)")
    rows = con.execute(
        f"SELECT itinerary_id, hub, partner_connection FROM {itineraries}"
    ).fetchall()
    if rows:
        con.executemany(
            "INSERT INTO _it_rules VALUES (?, ?)",
            [(i, rules.min_connection_for(h, partner=bool(p))) for i, h, p in rows],
        )
    start, end = period
    con.execute(
        f"""
        CREATE OR REPLACE TABLE {target} AS
        WITH it AS (
            SELECT i.itinerary_id, i.inbound, i.outbound, r.min_conn
            FROM {itineraries} i JOIN _it_rules r USING (itinerary_id)
        ),
        inb AS (
            SELECT it.itinerary_id, it.min_conn, it.outbound, f.*
            FROM it JOIN _inst f
              ON f.marketing_airline = it.inbound.marketing_airline
             AND f.flight_number = it.inbound.flight_number
             AND f.origin = it.inbound.origin AND f.dest = it.inbound.dest
            WHERE f.service_date BETWEEN DATE '{start}' AND DATE '{end}'
        ),
        m AS (
            SELECT inb.itinerary_id, inb.service_date, inb.min_conn,
                   inb.ok_n AS in_ok, inb.cancelled AS in_c, inb.diverted AS in_d,
                   inb.actual_arr AS in_arr,
                   o.ok_n AS out_ok, o.cancelled AS out_c, o.diverted AS out_d,
                   o.actual_dep AS out_dep, o.sched_dep AS out_sched,
                   row_number() OVER (
                       PARTITION BY inb.itinerary_id, inb.service_date
                       ORDER BY o.sched_dep NULLS LAST
                   ) AS rn
            FROM inb LEFT JOIN _inst o
              ON o.marketing_airline = inb.outbound.marketing_airline
             AND o.flight_number = inb.outbound.flight_number
             AND o.origin = inb.outbound.origin AND o.dest = inb.outbound.dest
             AND o.sched_dep >= inb.sched_arr + to_minutes(inb.min_conn)
             AND o.sched_dep <= inb.sched_arr + to_minutes({rules.max_layover_min})
        ),
        s AS (
            SELECT *,
                   CASE WHEN in_ok = 0 THEN 'quality'
                        WHEN out_sched IS NULL THEN 'not_connecting'
                        WHEN out_ok = 0 THEN 'quality'
                        ELSE 'paired' END AS status
            FROM m WHERE rn = 1
        )
        SELECT itinerary_id, service_date, status,
               CAST(min_conn AS INTEGER) AS min_connection_min,
               status = 'paired' AND (in_c OR out_c) AS any_cancelled,
               status = 'paired' AND (in_d OR out_d) AS any_diverted,
               CASE WHEN status = 'paired' AND NOT (in_c OR out_c OR in_d OR out_d)
                    THEN CAST((epoch(out_dep) - epoch(in_arr)) // 60 AS INTEGER) END
                   AS raw_slack_min
        FROM s
        ORDER BY itinerary_id, service_date
        """
    )


def classify(con: duckdb.DuckDBPyConnection, slack: str, boarding_cutoff: int, target: str) -> None:
    """Create ``target`` = ``slack`` plus ``outcome`` (null for excluded days)."""
    con.execute(
        f"""
        CREATE OR REPLACE TABLE {target} AS
        SELECT *,
               CASE WHEN status <> 'paired' THEN NULL
                    WHEN any_cancelled THEN 'cancelled'
                    WHEN any_diverted THEN 'diverted'
                    WHEN raw_slack_min >= {int(boarding_cutoff)} + min_connection_min
                        THEN 'feasible'
                    ELSE 'insufficient_time' END AS outcome
        FROM {slack}
        """
    )


def itinerary_results(
    con: duckdb.DuckDBPyConnection,
    classified: str,
    scenario_id: str,
    min_sample_days: int,
    period: tuple[dt.date, dt.date],
    target: str,
    itineraries: str | None = None,
) -> None:
    """Create ``target`` with ItineraryResult rows (data-model.md). With ``itineraries``,
    every itinerary gets a row, including ones with no scheduled days in the period."""
    pct = ",\n".join(
        f"CASE WHEN len(sl) = 0 THEN NULL "
        f"ELSE sl[CAST(floor({q} * (len(sl) - 1)) AS INTEGER) + 1] END AS {name}"
        for name, q in PERCENTILES.items()
    )
    base = (
        f"SELECT itinerary_id FROM {itineraries}"
        if itineraries
        else f"SELECT DISTINCT itinerary_id FROM {classified}"
    )
    start, end = period
    con.execute(
        f"""
        CREATE OR REPLACE TABLE {target} AS
        WITH agg AS (
            SELECT b.itinerary_id,
                   count(c.status) FILTER (WHERE c.status = 'paired') AS paired_days,
                   count(c.status) FILTER (WHERE c.status = 'not_connecting')
                       AS excluded_not_connecting,
                   count(c.status) FILTER (WHERE c.status = 'quality') AS excluded_quality,
                   count(c.status) FILTER (WHERE c.outcome = 'feasible') AS count_feasible,
                   count(c.status) FILTER (WHERE c.outcome = 'insufficient_time')
                       AS count_insufficient_time,
                   count(c.status) FILTER (WHERE c.outcome = 'cancelled') AS count_cancelled,
                   count(c.status) FILTER (WHERE c.outcome = 'diverted') AS count_diverted,
                   list_sort(coalesce(
                       list(c.raw_slack_min) FILTER (WHERE c.raw_slack_min IS NOT NULL),
                       []
                   )) AS sl
            FROM ({base}) b LEFT JOIN {classified} c USING (itinerary_id)
            GROUP BY b.itinerary_id
        )
        SELECT itinerary_id,
               '{scenario_id}' AS scenario_id,
               CAST(paired_days AS INTEGER) AS paired_days,
               CAST(excluded_not_connecting AS INTEGER) AS excluded_not_connecting,
               CAST(excluded_quality AS INTEGER) AS excluded_quality,
               CASE WHEN paired_days >= {int(min_sample_days)}
                    THEN round(count_feasible / paired_days, 6) END AS feasibility_rate,
               CASE WHEN paired_days >= {int(min_sample_days)} THEN 'ok'
                    ELSE 'insufficient_data' END AS status,
               CAST(count_feasible AS INTEGER) AS count_feasible,
               CAST(count_insufficient_time AS INTEGER) AS count_insufficient_time,
               CAST(count_cancelled AS INTEGER) AS count_cancelled,
               CAST(count_diverted AS INTEGER) AS count_diverted,
               CASE WHEN len(sl) = 0 THEN NULL ELSE sl[1] END AS slack_min,
               {pct},
               DATE '{start}' AS period_start,
               DATE '{end}' AS period_end
        FROM agg
        ORDER BY itinerary_id
        """
    )
