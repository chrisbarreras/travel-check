"""Schedule patterns and itinerary rules (ADR-0004, ADR-0013, FR-013 to FR-018a, research R6
and R12).

A *flight pattern* is marketing airline + flight number + origin + destination. Its recurrence
is the share of days in the period on which it was scheduled (cancelled flights count); an
itinerary's recurrence is the share of days on which its two flights connect.
Patterns are paired through a hub at the pattern level using their median scheduled local
times of day, so the pairing never joins every daily flight with every other. Layovers are
computed from local time of day at the hub (both times are in the same zone), which keeps a
pattern's typical layover stable across daylight-saving changes; daily matching (connection
days here, slack in the feasibility stage) always uses true UTC instants.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence

import duckdb

from flight_pipeline.config import Itineraries

# Shares are stored rounded to 6 decimals and compared as integers. With at most 366 days in
# a period, no k/days ratio lies within 1e-6 of a threshold, so rounding never moves a
# pattern or itinerary across it.
_SCALE = 1_000_000


def build_patterns(
    con: duckdb.DuckDBPyConnection,
    flights: str,
    period: tuple[dt.date, dt.date],
    target: str,
) -> None:
    """Create ``target``: one row per flight pattern with FlightPattern fields
    (``scheduled_days``, ``recurrence``) plus median schedule columns used for pairing:
    ``dep_local_min``, ``arr_local_min`` and ``elapsed_min``."""
    start, end = period
    days = (end - start).days + 1
    con.execute(
        f"""
        CREATE OR REPLACE TABLE {target} AS
        WITH daily AS (
            -- one row per pattern and date; identical or conflicting copies count once
            SELECT marketing_airline, flight_number, origin, dest, service_date,
                   min(sched_dep_local_min) AS dep_local,
                   min(sched_arr_local_min) AS arr_local,
                   min(sched_elapsed_min) AS elapsed
            FROM {flights}
            WHERE service_date BETWEEN DATE '{start}' AND DATE '{end}'
            GROUP BY ALL
        ),
        ref AS (
            SELECT marketing_airline, flight_number, origin, dest,
                   arg_min(dep_local, service_date) AS dep_ref,
                   arg_min(arr_local, service_date) AS arr_ref
            FROM daily GROUP BY ALL
        )
        SELECT d.marketing_airline, d.flight_number, d.origin, d.dest,
               CAST(count(*) AS INTEGER) AS scheduled_days,
               round(count(*) / {days}, 6) AS recurrence,
               CAST(((quantile_disc(((d.dep_local - r.dep_ref + 720) % 1440 + 1440) % 1440, 0.5)
                      + r.dep_ref - 720) % 1440 + 1440) % 1440 AS INTEGER) AS dep_local_min,
               CAST(((quantile_disc(((d.arr_local - r.arr_ref + 720) % 1440 + 1440) % 1440, 0.5)
                      + r.arr_ref - 720) % 1440 + 1440) % 1440 AS INTEGER) AS arr_local_min,
               CAST(quantile_disc(d.elapsed, 0.5) AS INTEGER) AS elapsed_min
        FROM daily d JOIN ref r USING (marketing_airline, flight_number, origin, dest)
        GROUP BY d.marketing_airline, d.flight_number, d.origin, d.dest, r.dep_ref, r.arr_ref
        ORDER BY d.marketing_airline, d.flight_number, d.origin, d.dest
        """
    )


def _rule_tables(
    con: duckdb.DuckDBPyConnection,
    hubs: Sequence[str],
    rules: Itineraries,
    od_pairs: Sequence[tuple[str, str]] | None,
) -> str:
    """Temporary rule tables; returns the SQL filter for ``od_pairs`` (empty when None)."""
    con.execute(
        "CREATE OR REPLACE TEMP TABLE _hub_rules "
        "(hub VARCHAR, min_same INTEGER, min_partner INTEGER)"
    )
    hub_rows = [
        (h, rules.min_connection_for(h, partner=False), rules.min_connection_for(h, partner=True))
        for h in sorted(set(hubs))
    ]
    if hub_rows:
        con.executemany("INSERT INTO _hub_rules VALUES (?, ?, ?)", hub_rows)
    con.execute("CREATE OR REPLACE TEMP TABLE _partners (a VARCHAR, b VARCHAR)")
    pairs = sorted({(a, b) for a, b in rules.partners} | {(b, a) for a, b in rules.partners})
    if pairs:
        con.executemany("INSERT INTO _partners VALUES (?, ?)", pairs)
    if od_pairs is None:
        return ""
    con.execute("CREATE OR REPLACE TEMP TABLE _od_only (origin VARCHAR, dest VARCHAR)")
    if od_pairs:
        con.executemany("INSERT INTO _od_only VALUES (?, ?)", sorted(set(od_pairs)))
    return "AND EXISTS (SELECT 1 FROM _od_only x WHERE x.origin = i.origin AND x.dest = o.dest)"


def build_itineraries(
    con: duckdb.DuckDBPyConnection,
    patterns: str,
    hubs: Sequence[str],
    rules: Itineraries,
    target: str,
    recurrence_threshold: float | None = None,
    *,
    flights: str,
    sold: str,
    period: tuple[dt.date, dt.date],
    od_pairs: Sequence[tuple[str, str]] | None = None,
) -> None:
    """Create ``target`` with the Itinerary columns (data-model.md), sorted by itinerary_id,
    and ``{target}_exclusions`` with OdExclusions rows for every origin/destination pair that
    has candidates. The rules run in the order of research R12:

    1. Candidates: an inbound pattern (origin to hub) and an outbound pattern (hub to
       destination), both scheduled on at least the recurrence threshold share of days, sold
       by the same marketing airline or a listed partner pair (never by operating airline).
    2. Median scheduled layover within [hub minimum, maximum]; partner connections use the
       partner minimum.
    3. Sold routing: the routing and its two selling airlines appear in ``sold``
       (SoldRouting rows) with at least ``min_sold_passengers`` sampled passengers.
    4. Connection-level recurrence: the share of days in ``period`` on which an outbound
       flight is scheduled within the layover limits after that day's scheduled inbound
       arrival is at least the recurrence threshold. This is the feasibility stage's daily
       matching on schedules only, so cancelled flights count as scheduled.

    The reported ``median_layover_min`` and ``median_travel_min`` are medians of the daily
    scheduled values (UTC) on the days the two flights connect, so they describe the itinerary
    as flown even when a flight changes its schedule during the period. Rule 2 uses the
    pattern medians, as a cheap pre-filter before the daily matching; when the two flights
    change schedule at different times it can exclude an itinerary that would connect.

    With ``od_pairs``, only those origin/destination pairs are built."""
    threshold = rules.recurrence_threshold if recurrence_threshold is None else recurrence_threshold
    threshold_scaled = round(threshold * _SCALE)
    start, end = period
    days = (end - start).days + 1
    od_filter = _rule_tables(con, hubs, rules, od_pairs)

    # Steps 1-3: candidates, flagged for the layover and sold-routing rules.
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _cand AS
        WITH p AS (
            SELECT * FROM {patterns}
            WHERE CAST(round(recurrence * {_SCALE}) AS BIGINT) >= {threshold_scaled}
        ),
        c AS (
            SELECT i.origin, i.dest AS hub, o.dest,
                   i.marketing_airline AS a1, i.flight_number AS n1,
                   o.marketing_airline AS a2, o.flight_number AS n2,
                   i.marketing_airline <> o.marketing_airline AS partner_connection,
                   ((o.dep_local_min - i.arr_local_min) % 1440 + 1440) % 1440 AS layover,
                   i.elapsed_min AS in_elapsed, o.elapsed_min AS out_elapsed,
                   i.dep_local_min AS dep_local,
                   CASE WHEN i.marketing_airline <> o.marketing_airline THEN h.min_partner
                        ELSE h.min_same END AS min_conn
            FROM p i
            JOIN _hub_rules h ON h.hub = i.dest
            JOIN p o ON o.origin = i.dest AND o.dest <> i.origin
            WHERE (i.marketing_airline = o.marketing_airline
                   OR EXISTS (SELECT 1 FROM _partners x
                              WHERE x.a = i.marketing_airline AND x.b = o.marketing_airline))
              {od_filter}
        )
        SELECT c.*,
               c.origin || '-' || c.hub || '-' || c.dest || ':' || c.a1 || CAST(c.n1 AS VARCHAR)
                   || '+' || c.a2 || CAST(c.n2 AS VARCHAR) AS itinerary_id,
               c.layover >= c.min_conn AND c.layover <= {rules.max_layover_min} AS layover_ok,
               CAST(coalesce(s.passengers, 0) AS INTEGER) AS sold_passengers,
               coalesce(s.passengers, 0) >= {rules.min_sold_passengers} AS sold_ok
        FROM c
        LEFT JOIN {sold} s
          ON s.origin = c.origin AND s.hub = c.hub AND s.dest = c.dest
         AND s.airline_in = c.a1 AND s.airline_out = c.a2
        """
    )

    # Step 4, only for candidates that passed steps 2 and 3. For each in-period inbound day,
    # the earliest outbound scheduled at or after arrival + minimum (ASOF join) connects when
    # it also leaves within the maximum layover.
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _sched AS
        SELECT marketing_airline, flight_number, origin, dest, service_date,
               min(sched_dep_utc) AS sched_dep, min(sched_arr_utc) AS sched_arr
        FROM {flights}
        WHERE quality_flag <> 'duplicate'
        GROUP BY ALL
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _connect AS
        WITH inb AS (
            SELECT c.itinerary_id, c.a2, c.n2, c.hub, c.dest,
                   f.sched_dep AS in_dep, f.sched_arr AS in_arr,
                   f.sched_arr + to_minutes(c.min_conn) AS earliest,
                   f.sched_arr + to_minutes({rules.max_layover_min}) AS latest
            FROM _cand c
            JOIN _sched f
              ON f.marketing_airline = c.a1 AND f.flight_number = c.n1
             AND f.origin = c.origin AND f.dest = c.hub
            WHERE c.layover_ok AND c.sold_ok
              AND f.service_date BETWEEN DATE '{start}' AND DATE '{end}'
        )
        , m AS (
            SELECT inb.itinerary_id, inb.in_dep, inb.in_arr,
                   o.sched_dep AS out_dep, o.sched_arr AS out_arr,
                   coalesce(o.sched_dep <= inb.latest, false) AS connects
            FROM inb ASOF LEFT JOIN _sched o
              ON o.marketing_airline = inb.a2 AND o.flight_number = inb.n2
             AND o.origin = inb.hub AND o.dest = inb.dest
             AND inb.earliest <= o.sched_dep
        )
        SELECT itinerary_id,
               round(count(*) FILTER (WHERE connects) / {days}, 6) AS connect_share,
               quantile_disc((epoch(out_dep) - epoch(in_arr)) // 60, 0.5)
                   FILTER (WHERE connects) AS day_layover,
               quantile_disc((epoch(out_arr) - epoch(in_dep)) // 60, 0.5)
                   FILTER (WHERE connects) AS day_travel
        FROM m
        GROUP BY itinerary_id
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _cand_ok AS
        SELECT c.*, coalesce(k.connect_share, 0.0) AS connect_share,
               k.day_layover, k.day_travel,
               c.layover_ok AND c.sold_ok
                   AND CAST(round(coalesce(k.connect_share, 0.0) * {_SCALE}) AS BIGINT)
                       >= {threshold_scaled} AS recurrence_ok
        FROM _cand c LEFT JOIN _connect k USING (itinerary_id)
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TABLE {target} AS
        SELECT itinerary_id, origin, hub, dest,
               struct_pack(marketing_airline := a1, flight_number := n1,
                           origin := origin, dest := hub) AS inbound,
               struct_pack(marketing_airline := a2, flight_number := n2,
                           origin := hub, dest := dest) AS outbound,
               partner_connection,
               CAST(coalesce(day_layover, layover) AS INTEGER) AS median_layover_min,
               CAST(coalesce(day_travel, in_elapsed + layover + out_elapsed) AS INTEGER)
                   AS median_travel_min,
               CAST(dep_local AS INTEGER) AS median_dep_local_min,
               connect_share,
               sold_passengers
        FROM _cand_ok
        WHERE recurrence_ok
        ORDER BY itinerary_id
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TABLE {target}_exclusions AS
        SELECT origin, dest,
               CAST(count(*) AS INTEGER) AS candidates,
               CAST(count(*) FILTER (WHERE NOT layover_ok) AS INTEGER) AS excluded_layover,
               CAST(count(*) FILTER (WHERE layover_ok AND NOT sold_ok) AS INTEGER)
                   AS excluded_unsold,
               CAST(count(*) FILTER (WHERE layover_ok AND sold_ok AND NOT recurrence_ok)
                   AS INTEGER) AS excluded_recurrence,
               CAST(count(*) FILTER (WHERE recurrence_ok) AS INTEGER) AS qualifying
        FROM _cand_ok
        GROUP BY origin, dest
        ORDER BY origin, dest
        """
    )
    for t in ("_cand", "_sched", "_connect", "_cand_ok"):
        con.execute(f"DROP TABLE IF EXISTS {t}")
