"""Itineraries from schedule slots (ADR-0004, ADR-0013, ADR-0014; specs/002 research R1-R2).

An itinerary is an inbound schedule slot (origin to hub) and an outbound slot (hub to
destination). The rules run in this order (research R2):

1. **Candidates**: airline-compatible slot pairs through a hub (same marketing airline or a
   listed partner pair, never the operating airline), each slot scheduled on at least the
   recurrence threshold share of days (a necessary condition for rule 4).
2. **Bounds** (lossless pre-filter): a pair is dropped only when no combination of the
   inbound slot's local arrival times and the outbound slot's local departure times can give
   a layover within the limits, allowing 60 minutes for a daylight-saving night.
3. **Sold routing**: DB1B shows at least the minimum sampled passengers on the routing and
   pair of selling airlines (ADR-0013).
4. **Daily matching and connection-level recurrence**: on each in-period day the inbound
   slot flies, the earliest outbound flight of the outbound slot scheduled at least the
   minimum connection time after the inbound's scheduled arrival connects if it leaves
   within the maximum layover. A day whose matching window runs past the loaded data is
   excluded (end of period) rather than counted as not connecting. The share of connecting
   days must reach the recurrence threshold.

Reported layover and travel time are medians of the daily scheduled values (UTC) on the
connecting days.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence

import duckdb

from flight_pipeline.config import Itineraries

# Shares are rounded to 6 decimals and compared as integers. With at most 366 days in a
# period, no k/days ratio lies within 1e-6 of a threshold, so rounding never moves an
# itinerary across it.
_SCALE = 1_000_000
DST_SLACK_MIN = 60


def bounds_allow(
    arrivals: Sequence[int], departures: Sequence[int], min_conn: int, max_layover: int
) -> bool:
    """True when some local arrival and departure time of day could give a layover within
    [min_conn, max_layover] on some day, allowing a daylight-saving shift of up to 60 minutes.
    Never False for a pair that connects (research R2)."""
    lo, hi = min_conn - DST_SLACK_MIN, max_layover + DST_SLACK_MIN
    return any(lo <= (d - a) % 1440 <= hi for a in arrivals for d in departures)


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


def _slot_instances(con: duckdb.DuckDBPyConnection, flights: str, slots: str) -> None:
    """``_slot_inst``: one row per flight-day of a candidate's slot (``_cand``) with scheduled
    UTC instants, the local arrival minute and the flight's identity (for quality and actual
    times later)."""
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _slot_inst AS
        SELECT d.slot_id, d.service_date, d.marketing_airline, d.flight_number, d.origin, d.dest,
               min(f.sched_dep_utc) AS sched_dep, min(f.sched_arr_utc) AS sched_arr,
               min(f.sched_arr_local_min) AS arr_local
        FROM (
            SELECT * FROM {slots}_days
            WHERE slot_id IN (SELECT in_slot FROM _cand UNION SELECT out_slot FROM _cand)
        ) d
        JOIN {flights} f
          ON f.marketing_airline = d.marketing_airline AND f.flight_number = d.flight_number
         AND f.origin = d.origin AND f.dest = d.dest AND f.service_date = d.service_date
        GROUP BY ALL
        """
    )


def build_itineraries(
    con: duckdb.DuckDBPyConnection,
    slots: str,
    hubs: Sequence[str],
    rules: Itineraries,
    target: str,
    recurrence_threshold: float | None = None,
    *,
    flights: str,
    sold: str,
    period: tuple[dt.date, dt.date],
    od_pairs: Sequence[tuple[str, str]] | None = None,
    days: bool = True,
) -> None:
    """Create ``target`` (Itinerary rows, data-model.md), ``{target}_exclusions`` (OdExclusions
    per origin/destination pair with candidates) and ``{target}_days`` (the daily matching of
    qualifying itineraries: itinerary_id, service_date, status, the inbound and outbound
    flight-days, min_connection_min), from ``slots``, ``{slots}_days`` and ``flights``.

    The daily matching runs one hub at a time, which keeps memory bounded on a full year;
    every result is per itinerary, so the split never changes it. With ``days=False`` the
    ``{target}_days`` table is not created (callers that need only the itineraries)."""
    threshold = rules.recurrence_threshold if recurrence_threshold is None else recurrence_threshold
    threshold_scaled = round(threshold * _SCALE)
    start, end = period
    od_filter = _rule_tables(con, hubs, rules, od_pairs)

    # 1. Candidates
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _cand AS
        WITH s AS (
            SELECT * FROM {slots}
            WHERE CAST(round(recurrence * {_SCALE}) AS BIGINT) >= {threshold_scaled}
        )
        SELECT i.origin, i.dest AS hub, o.dest,
               i.slot_id AS in_slot, o.slot_id AS out_slot,
               i.marketing_airline AS a1, o.marketing_airline AS a2,
               i.marketing_airline <> o.marketing_airline AS partner_connection,
               i.ref_dep_local_min AS dep_local,
               CASE WHEN i.marketing_airline <> o.marketing_airline THEN h.min_partner
                    ELSE h.min_same END AS min_conn,
               i.origin || '-' || i.dest || '-' || o.dest || ':' || i.marketing_airline
                   || split_part(i.slot_id, '-', 4)
                   || CASE WHEN len(string_split(i.slot_id, '-')) > 4
                           THEN '-' || split_part(i.slot_id, '-', 5) ELSE '' END
                   || '+' || o.marketing_airline || split_part(o.slot_id, '-', 4)
                   || CASE WHEN len(string_split(o.slot_id, '-')) > 4
                           THEN '-' || split_part(o.slot_id, '-', 5) ELSE '' END
                   AS itinerary_id
        FROM s i
        JOIN _hub_rules h ON h.hub = i.dest
        JOIN s o ON o.origin = i.dest AND o.dest <> i.origin
        WHERE (i.marketing_airline = o.marketing_airline
               OR EXISTS (SELECT 1 FROM _partners x
                          WHERE x.a = i.marketing_airline AND x.b = o.marketing_airline))
          {od_filter}
        """
    )

    _slot_instances(con, flights, slots)

    # 2. Bounds (lossless): some local arrival x departure combination within the limits
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _bounds_ok AS
        WITH arr AS (SELECT DISTINCT slot_id, arr_local FROM _slot_inst),
             dep AS (SELECT DISTINCT slot_id, dep_local_min AS dep_local FROM {slots}_days)
        SELECT DISTINCT c.itinerary_id
        FROM _cand c
        JOIN arr a ON a.slot_id = c.in_slot
        JOIN dep d ON d.slot_id = c.out_slot
        WHERE ((d.dep_local - a.arr_local) % 1440 + 1440) % 1440
              BETWEEN c.min_conn - {DST_SLACK_MIN} AND {rules.max_layover_min + DST_SLACK_MIN}
        """
    )

    # 3. Sold routing
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _cand_flags AS
        SELECT c.*,
               b.itinerary_id IS NOT NULL AS bounds_ok,
               CAST(coalesce(s.passengers, 0) AS INTEGER) AS sold_passengers,
               coalesce(s.passengers, 0) >= {rules.min_sold_passengers} AS sold_ok
        FROM _cand c
        LEFT JOIN _bounds_ok b USING (itinerary_id)
        LEFT JOIN {sold} s
          ON s.origin = c.origin AND s.hub = c.hub AND s.dest = c.dest
         AND s.airline_in = c.a1 AND s.airline_out = c.a2
        """
    )

    # 4. Daily matching for the candidates that passed 2 and 3, one hub at a time
    hub_list = [
        r[0]
        for r in con.execute(
            "SELECT DISTINCT hub FROM _cand_flags WHERE bounds_ok AND sold_ok ORDER BY hub"
        ).fetchall()
    ]
    con.execute(
        "CREATE OR REPLACE TEMP TABLE _agg (itinerary_id VARCHAR, eligible_days BIGINT, "
        "connect_days BIGINT, layover DOUBLE, travel DOUBLE)"
    )
    con.execute("DROP TABLE IF EXISTS _match_all")
    if not days:
        _lean_keys(con)
    # An empty hub list still runs once so that _match (and _match_all) have their columns.
    for i, hub in enumerate(hub_list or [""]):
        if not days:
            _lean_agg_hub(con, hub, rules.max_layover_min, start, end)
            continue
        _match_hub(con, hub, rules.max_layover_min, start, end)
        con.execute(f"INSERT INTO _agg SELECT itinerary_id, {_AGG_COLUMNS} FROM _match GROUP BY 1")
        if i == 0:
            con.execute("CREATE TEMP TABLE _match_all AS SELECT * FROM _match")
        else:
            con.execute("INSERT INTO _match_all SELECT * FROM _match")
        con.execute("DROP TABLE _match")
    _finish(con, target, threshold_scaled, days=days)


# Per-itinerary results of the daily matching (rule 4): eligible days, connecting days and
# the median scheduled layover and travel time over connecting days.
_AGG_COLUMNS = """
    count(*) FILTER (WHERE status <> 'end_of_period'),
    count(*) FILTER (WHERE status = 'connects'),
    quantile_disc((epoch(out_dep) - epoch(in_arr)) // 60, 0.5)
        FILTER (WHERE status = 'connects'),
    quantile_disc((epoch(out_arr) - epoch(in_dep)) // 60, 0.5)
        FILTER (WHERE status = 'connects')
"""

# The local-minus-UTC offset of the inbound arrival, in minutes (-720..719).
_OFFSET_SQL = """(((f.arr_local - (hour(f.sched_arr) * 60 + minute(f.sched_arr))) % 1440
                     + 1440 + 720) % 1440) - 720"""


def _status_sql(end: dt.date) -> str:
    """The day's matching status (rule 4), from ``out_dep``, ``latest`` and ``offset_min``."""
    return f"""
        CASE WHEN out_dep IS NOT NULL AND out_dep <= latest THEN 'connects'
             WHEN CAST(latest + to_minutes(CAST(offset_min AS INTEGER)) AS DATE)
                  > DATE '{end}' THEN 'end_of_period'
             ELSE 'not_connecting' END"""


def _lean_keys(con: duckdb.DuckDBPyConnection) -> None:
    """Integer keys for the matching when only the per-itinerary results are needed: narrow
    rows keep the full year's matching of every candidate within memory."""
    con.execute(
        """
        CREATE OR REPLACE TEMP TABLE _slot_keys AS
        SELECT slot_id, CAST(row_number() OVER (ORDER BY slot_id) AS INTEGER) AS slot_key
        FROM (SELECT DISTINCT slot_id FROM _slot_inst)
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TEMP TABLE _slot_lean AS
        SELECT k.slot_key, s.service_date, s.sched_dep, s.sched_arr, s.arr_local
        FROM _slot_inst s JOIN _slot_keys k USING (slot_id)
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TEMP TABLE _cand_keys AS
        SELECT c.itinerary_id, c.hub, c.min_conn,
               CAST(row_number() OVER (ORDER BY c.itinerary_id) AS INTEGER) AS cand_key,
               ki.slot_key AS in_key, ko.slot_key AS out_key
        FROM _cand_flags c
        JOIN _slot_keys ki ON ki.slot_id = c.in_slot
        JOIN _slot_keys ko ON ko.slot_id = c.out_slot
        WHERE c.bounds_ok AND c.sold_ok
        """
    )


def _lean_agg_hub(
    con: duckdb.DuckDBPyConnection, hub: str, max_layover: int, start: dt.date, end: dt.date
) -> None:
    """Add one hub's per-itinerary matching results to ``_agg`` without keeping the days:
    the same matching as ``_match_hub``, on integer keys and only the columns it needs.
    Each step is its own table: DuckDB plans the fused query far worse on large hubs."""
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _lean_inb AS
        SELECT k.cand_key, k.out_key,
               f.sched_dep AS in_dep, f.sched_arr AS in_arr,
               f.sched_arr + to_minutes(k.min_conn) AS earliest,
               f.sched_arr + to_minutes({max_layover}) AS latest,
               {_OFFSET_SQL} AS offset_min
        FROM _cand_keys k
        JOIN _slot_lean f ON f.slot_key = k.in_key
        WHERE k.hub = $hub AND f.service_date BETWEEN DATE '{start}' AND DATE '{end}'
        """,
        {"hub": hub},
    )
    con.execute(
        """
        CREATE OR REPLACE TEMP TABLE _lean_m AS
        SELECT inb.*, o.sched_dep AS out_dep, o.sched_arr AS out_arr
        FROM _lean_inb inb ASOF LEFT JOIN _slot_lean o
          ON o.slot_key = inb.out_key AND inb.earliest <= o.sched_dep
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _lean_s AS
        SELECT cand_key, in_dep, in_arr, out_dep, out_arr, {_status_sql(end)} AS status
        FROM _lean_m
        """
    )
    con.execute(
        f"""
        INSERT INTO _agg
        SELECT k.itinerary_id, a.* EXCLUDE (cand_key)
        FROM (SELECT cand_key, {_AGG_COLUMNS} FROM _lean_s GROUP BY cand_key) a
        JOIN _cand_keys k USING (cand_key)
        """
    )
    for t in ("_lean_inb", "_lean_m", "_lean_s"):
        con.execute(f"DROP TABLE {t}")


def _match_hub(
    con: duckdb.DuckDBPyConnection, hub: str, max_layover: int, start: dt.date, end: dt.date
) -> None:
    """``_match``: the daily matching (rule 4) of one hub's candidates, in steps as in
    ``_lean_agg_hub``."""
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _match_inb AS
        SELECT c.itinerary_id, c.out_slot, c.min_conn,
               f.service_date, f.marketing_airline AS in_airline,
               f.flight_number AS in_number, f.origin AS in_origin, f.dest AS in_dest,
               f.sched_dep AS in_dep, f.sched_arr AS in_arr,
               f.sched_arr + to_minutes(c.min_conn) AS earliest,
               f.sched_arr + to_minutes({max_layover}) AS latest,
               {_OFFSET_SQL} AS offset_min
        FROM _cand_flags c
        JOIN _slot_inst f ON f.slot_id = c.in_slot
        WHERE c.bounds_ok AND c.sold_ok AND c.hub = $hub
          AND f.service_date BETWEEN DATE '{start}' AND DATE '{end}'
        """,
        {"hub": hub},
    )
    con.execute(
        """
        CREATE OR REPLACE TEMP TABLE _match_m AS
        SELECT inb.*, o.service_date AS out_date, o.marketing_airline AS out_airline,
               o.flight_number AS out_number, o.origin AS out_origin, o.dest AS out_dest,
               o.sched_dep AS out_dep, o.sched_arr AS out_arr
        FROM _match_inb inb ASOF LEFT JOIN _slot_inst o
          ON o.slot_id = inb.out_slot AND inb.earliest <= o.sched_dep
        """
    )
    con.execute(
        f"CREATE OR REPLACE TEMP TABLE _match AS SELECT *, {_status_sql(end)} AS status "
        "FROM _match_m"
    )
    for t in ("_match_inb", "_match_m"):
        con.execute(f"DROP TABLE {t}")


def _finish(
    con: duckdb.DuckDBPyConnection, target: str, threshold_scaled: int, *, days: bool
) -> None:
    """Qualification, ``target``, ``{target}_exclusions`` and (with ``days``) ``{target}_days``."""
    con.execute(
        """
        CREATE OR REPLACE TEMP TABLE _cand_ok AS
        SELECT c.*, coalesce(a.eligible_days, 0) AS eligible_days,
               coalesce(a.connect_days, 0) AS connect_days, a.layover, a.travel,
               CASE WHEN coalesce(a.eligible_days, 0) = 0 THEN 0.0
                    ELSE round(a.connect_days / a.eligible_days, 6) END AS connect_share
        FROM _cand_flags c LEFT JOIN _agg a USING (itinerary_id)
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _cand_ok2 AS
        SELECT *,
               bounds_ok AND sold_ok AND connect_days > 0
                   AND CAST(round(connect_share * {_SCALE}) AS BIGINT) >= {threshold_scaled}
                   AS qualifies
        FROM _cand_ok
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TABLE {target} AS
        SELECT itinerary_id, origin, hub, dest, in_slot AS inbound_slot, out_slot AS outbound_slot,
               a1 AS airline_in, a2 AS airline_out, partner_connection,
               CAST(layover AS INTEGER) AS median_layover_min,
               CAST(travel AS INTEGER) AS median_travel_min,
               CAST(dep_local AS INTEGER) AS median_dep_local_min,
               connect_share,
               CAST(eligible_days AS INTEGER) AS eligible_days,
               sold_passengers,
               CAST(count(*) OVER (PARTITION BY origin, hub, dest, a1, a2) AS INTEGER)
                   AS routing_itineraries
        FROM _cand_ok2
        WHERE qualifies
        ORDER BY itinerary_id
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TABLE {target}_exclusions AS
        SELECT origin, dest,
               CAST(count(*) AS INTEGER) AS candidates,
               CAST(count(*) FILTER (WHERE NOT bounds_ok) AS INTEGER) AS excluded_bounds,
               CAST(count(*) FILTER (WHERE bounds_ok AND NOT sold_ok) AS INTEGER)
                   AS excluded_unsold,
               CAST(count(*) FILTER (WHERE bounds_ok AND sold_ok AND connect_days = 0)
                   AS INTEGER) AS excluded_not_connecting,
               CAST(count(*) FILTER (WHERE bounds_ok AND sold_ok AND connect_days > 0
                                     AND NOT qualifies) AS INTEGER) AS excluded_recurrence,
               CAST(count(*) FILTER (WHERE qualifies) AS INTEGER) AS qualifying
        FROM _cand_ok2
        GROUP BY origin, dest
        ORDER BY origin, dest
        """
    )
    if days:
        _days_table(con, target)
    for t in (
        "_cand",
        "_bounds_ok",
        "_cand_flags",
        "_match_all",
        "_agg",
        "_cand_ok",
        "_cand_ok2",
        "_slot_keys",
        "_slot_lean",
        "_cand_keys",
    ):
        con.execute(f"DROP TABLE IF EXISTS {t}")


def _days_table(con: duckdb.DuckDBPyConnection, target: str) -> None:
    con.execute(
        f"""
        CREATE OR REPLACE TABLE {target}_days AS
        SELECT m.itinerary_id, m.service_date, m.status AS match_status,
               m.status = 'connects' AS match_status_ok,
               CAST(m.min_conn AS INTEGER) AS min_connection_min,
               m.in_airline, m.in_number, m.in_origin, m.in_dest,
               m.out_airline, m.out_number, m.out_origin, m.out_dest, m.out_date,
               m.in_dep, m.in_arr, m.out_dep, m.out_arr
        FROM _match_all m JOIN {target} t USING (itinerary_id)
        ORDER BY m.itinerary_id, m.service_date
        """
    )
