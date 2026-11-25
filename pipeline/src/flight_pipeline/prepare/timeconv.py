"""Local schedule plus delay minutes -> UTC instants (ADR-0008, research R3).

    scheduled departure = FlightDate + CRSDepTime in the origin's zone, converted to UTC
    scheduled arrival   = scheduled departure + CRSElapsedTime
    actual departure    = scheduled departure + DepDelay
    actual arrival      = actual departure + ActualElapsedTime

Only the scheduled departure needs a zone lookup; everything else is minute arithmetic in UTC,
so dates are never guessed from clock times. Lookups use offset tables built with zoneinfo:
every relevant zone changes offset only on whole hours, so scanning hourly and compressing
runs of equal offsets is exact. Non-existent local times (spring forward) and repeated ones
(fall back) resolve with ``fold=0``, exactly as zoneinfo does.

Timestamps are stored naive and always mean UTC, so the DuckDB session time zone never matters.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable
from zoneinfo import ZoneInfo

import duckdb

UTC = dt.UTC
_HOUR = dt.timedelta(hours=1)


def hhmm_minutes(value: str | int) -> int:
    """BTS ``HHMM`` (e.g. ``"0830"``, ``"5"``, ``"2400"``) -> minutes after midnight, 0-1440."""
    try:
        v = int(str(value).strip())
    except ValueError:
        raise ValueError(f"not a valid HHMM time: {value!r}") from None
    hours, minutes = divmod(v, 100)
    if v < 0 or minutes >= 60 or v > 2400:
        raise ValueError(f"not a valid HHMM time: {value!r}")
    return hours * 60 + minutes


def local_minute_of_day(value: str | int) -> int:
    """Time of day in minutes, 0-1439 (``2400`` -> 0)."""
    return hhmm_minutes(value) % 1440


def local_to_utc(day: dt.date, minutes: int, tz: str) -> dt.datetime:
    """Reference conversion: local midnight of ``day`` plus ``minutes`` in ``tz``, as UTC."""
    local = dt.datetime.combine(day, dt.time()) + dt.timedelta(minutes=minutes)
    return local.replace(tzinfo=ZoneInfo(tz), fold=0).astimezone(UTC)


def _offset_minutes(delta: dt.timedelta | None) -> int:
    assert delta is not None
    return int(delta.total_seconds() // 60)


def _runs(
    hours: list[dt.datetime], offsets: list[int]
) -> list[tuple[dt.datetime, dt.datetime, int]]:
    out: list[tuple[dt.datetime, dt.datetime, int]] = []
    start, current = hours[0], offsets[0]
    for h, off in zip(hours[1:], offsets[1:], strict=True):
        if off != current:
            out.append((start, h, current))
            start, current = h, off
    out.append((start, hours[-1] + _HOUR, current))
    return out


def offset_intervals(
    tz: str, start: dt.date, end: dt.date
) -> tuple[list[tuple[dt.datetime, dt.datetime, int]], list[tuple[dt.datetime, dt.datetime, int]]]:
    """Constant-offset intervals for ``tz`` as (start, end, offset minutes), in local naive
    time and in UTC naive time. Covers ``start`` - 2 days to ``end`` + 5 days, enough for
    ``2400`` departures and arrivals several days after the period."""
    zone = ZoneInfo(tz)
    first = dt.datetime.combine(start - dt.timedelta(days=2), dt.time())
    last = dt.datetime.combine(end + dt.timedelta(days=5), dt.time())
    hours: list[dt.datetime] = []
    h = first
    while h <= last:
        hours.append(h)
        h += _HOUR
    local_offsets = [_offset_minutes(x.replace(tzinfo=zone, fold=0).utcoffset()) for x in hours]
    utc_offsets = [
        _offset_minutes(x.replace(tzinfo=UTC).astimezone(zone).utcoffset()) for x in hours
    ]
    return _runs(hours, local_offsets), _runs(hours, utc_offsets)


def build_offset_tables(
    con: duckdb.DuckDBPyConnection, zones: Iterable[str], start: dt.date, end: dt.date
) -> None:
    """Create ``tz_local_offsets`` (tz, local_start, local_end, offset_min) and
    ``tz_utc_offsets`` (tz, utc_start, utc_end, offset_min). UTC = local - offset."""
    local_rows: list[tuple[str, dt.datetime, dt.datetime, int]] = []
    utc_rows: list[tuple[str, dt.datetime, dt.datetime, int]] = []
    for tz in sorted(set(zones)):
        local, utc = offset_intervals(tz, start, end)
        local_rows += [(tz, a, b, o) for a, b, o in local]
        utc_rows += [(tz, a, b, o) for a, b, o in utc]
    for table, cols, rows in (
        ("tz_local_offsets", "local_start TIMESTAMP, local_end TIMESTAMP", local_rows),
        ("tz_utc_offsets", "utc_start TIMESTAMP, utc_end TIMESTAMP", utc_rows),
    ):
        con.execute(f"CREATE OR REPLACE TABLE {table} (tz VARCHAR, {cols}, offset_min INTEGER)")
        con.executemany(f"INSERT INTO {table} VALUES (?, ?, ?, ?)", rows)


def add_instants(con: duckdb.DuckDBPyConnection, source: str, target: str) -> None:
    """Create ``target`` = ``source`` plus ``sched_dep_utc``, ``sched_arr_utc``,
    ``actual_dep_utc`` and ``actual_arr_utc``.

    ``source`` needs ``service_date``, ``crs_dep_min`` (0-1440), ``sched_elapsed_min``,
    ``dep_delay_min`` (null if the flight never departed), ``actual_elapsed_min`` (null if it
    never arrived) and ``origin_tz``. Rows whose zone or date falls outside the offset tables
    are an error, not silently dropped."""
    con.execute(
        f"""
        CREATE OR REPLACE TABLE {target} AS
        WITH s AS (
            SELECT *, CAST(service_date AS TIMESTAMP) + to_minutes(crs_dep_min) AS _local_dep
            FROM {source}
        ),
        d AS (
            SELECT s.* EXCLUDE (_local_dep),
                   s._local_dep - to_minutes(o.offset_min) AS sched_dep_utc
            FROM s
            LEFT JOIN tz_local_offsets o
              ON o.tz = s.origin_tz AND s._local_dep >= o.local_start AND s._local_dep < o.local_end
        )
        SELECT *,
               sched_dep_utc + to_minutes(sched_elapsed_min) AS sched_arr_utc,
               sched_dep_utc + to_minutes(dep_delay_min) AS actual_dep_utc,
               sched_dep_utc + to_minutes(dep_delay_min) + to_minutes(actual_elapsed_min)
                   AS actual_arr_utc
        FROM d
        """
    )
    row = con.execute(f"SELECT count(*) FROM {target} WHERE sched_dep_utc IS NULL").fetchone()
    missing = 0 if row is None else int(row[0])
    if missing:
        raise ValueError(
            f"{missing} row(s) could not be converted to UTC (zone or date outside the "
            "offset tables)"
        )
