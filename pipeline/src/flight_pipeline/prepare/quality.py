"""Data-quality flags and checks (FR-005, research R3).

Rows with an invalid schedule (missing or non-positive ``CRSElapsedTime``, bad ``HHMM``)
are corrupt source records: they are dropped before conversion and counted as
``invalid_schedule`` in quality.json.

Flags, in precedence order (data-model.md FlightRecord.quality_flag):

1. ``conflicting_duplicate``: several records share one identity and disagree; all excluded.
2. ``duplicate``: identical copies of one record; one copy stays ``ok``.
3. ``missing_actual_times``: an operated flight without actual times.
4. ``clock_time_mismatch``: computed actual instants disagree with the BTS clock times
   (``DepTime``/``ArrTime``) by more than 1 minute. If the share of such flights among those
   checked exceeds the configured limit, the run fails.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import duckdb

IDENTITY = ("marketing_airline", "flight_number", "service_date", "origin")
FLAG_NAMES = ("duplicate", "conflicting_duplicate", "missing_actual_times", "clock_time_mismatch")
# Fields compared to decide whether copies of one identity are identical.
SIGNATURE_FIELDS = (
    "operating_airline",
    "dest",
    "crs_dep_min",
    "sched_arr_local_min",
    "sched_elapsed_min",
    "dep_delay_min",
    "actual_elapsed_min",
    "dep_time_min",
    "arr_time_min",
    "cancelled",
    "diverted",
    "cancellation_code",
    "weather_delay_min",
)


class QualityError(RuntimeError):
    """The data failed a quality gate; the run must stop (exit code 1)."""

    def __init__(self, message: str, report: QualityReport) -> None:
        super().__init__(message)
        self.report = report


@dataclass
class QualityReport:
    by_month: dict[str, dict[str, int]] = field(default_factory=dict[str, dict[str, int]])
    clock_checked: int = 0
    clock_mismatch: int = 0
    clock_mismatch_max_share: float = 0.0
    sched_arr_mismatch: int = 0

    @property
    def clock_mismatch_share(self) -> float:
        return self.clock_mismatch / self.clock_checked if self.clock_checked else 0.0

    def add_invalid_schedule(self, by_month: dict[str, int]) -> None:
        """Record rows dropped before conversion because their schedule is invalid."""
        for counts in self.by_month.values():
            counts.setdefault("invalid_schedule", 0)
        for month, n in by_month.items():
            self.by_month.setdefault(month, {"rows": 0})["invalid_schedule"] = n

    def totals(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for counts in self.by_month.values():
            for k, v in counts.items():
                out[k] = out.get(k, 0) + v
        return out

    def to_json(self) -> dict[str, Any]:
        return {
            "by_month": {m: dict(sorted(c.items())) for m, c in sorted(self.by_month.items())},
            "totals": dict(sorted(self.totals().items())),
            "clock_checked": self.clock_checked,
            "clock_mismatch": self.clock_mismatch,
            "clock_mismatch_share": round(self.clock_mismatch_share, 6),
            "clock_mismatch_max_share": self.clock_mismatch_max_share,
            "sched_arr_mismatch": self.sched_arr_mismatch,
        }


def _circular(expr: str) -> str:
    """Smallest distance in minutes between two times of day, given their difference."""
    m = f"((({expr}) % 1440 + 1440) % 1440)"
    return f"least({m}, 1440 - {m})"


def _local_minute(ts: str, tz: str, alias: str) -> str:
    return (
        f"(SELECT CAST(extract('hour' FROM {ts} + to_minutes(o.offset_min)) * 60 "
        f"+ extract('minute' FROM {ts} + to_minutes(o.offset_min)) AS INTEGER) "
        f"FROM tz_utc_offsets o WHERE o.tz = {tz} "
        f"AND {ts} >= o.utc_start AND {ts} < o.utc_end) AS {alias}"
    )


def flag_quality(
    con: duckdb.DuckDBPyConnection, source: str, target: str, max_share: float
) -> QualityReport:
    """Create ``target`` = ``source`` plus ``quality_flag``. Raises QualityError when the
    clock-time mismatch share exceeds ``max_share`` (the table is still written)."""
    ident = ", ".join(IDENTITY)
    sig = " || '|' || ".join(f"coalesce(CAST({f} AS VARCHAR), '<null>')" for f in SIGNATURE_FIELDS)
    dep_diff = _circular("crs_dep_min + dep_delay_min - dep_time_min")
    arr_diff = _circular("arr_local_min - arr_time_min")
    con.execute(
        f"""
        CREATE OR REPLACE TABLE {target} AS
        WITH s AS (
            SELECT *, md5({sig}) AS _sig,
                   {_local_minute("actual_arr_utc", "dest_tz", "arr_local_min")},
                   {_local_minute("sched_arr_utc", "dest_tz", "sched_arr_check_min")}
            FROM {source}
        ),
        g AS (
            SELECT {ident}, count(*) AS _n, count(DISTINCT _sig) AS _nd
            FROM s GROUP BY ALL
        ),
        j AS (
            SELECT s.*, g._n, g._nd,
                   row_number() OVER (PARTITION BY s.{IDENTITY[0]}, s.{IDENTITY[1]},
                                      s.{IDENTITY[2]}, s.{IDENTITY[3]} ORDER BY s._sig) AS _rn,
                   (NOT s.cancelled AND NOT s.diverted
                    AND s.dep_time_min IS NOT NULL AND s.arr_time_min IS NOT NULL
                    AND s.actual_dep_utc IS NOT NULL AND s.actual_arr_utc IS NOT NULL)
                       AS clock_checked,
                   ({dep_diff} > 1 OR {arr_diff} > 1) AS _clock_bad
            FROM s JOIN g USING ({ident})
        )
        SELECT * EXCLUDE (_sig, _n, _nd, _rn, _clock_bad, arr_local_min),
               CASE
                   WHEN _n > 1 AND _nd > 1 THEN 'conflicting_duplicate'
                   WHEN _n > 1 AND _rn > 1 THEN 'duplicate'
                   WHEN NOT cancelled AND NOT diverted
                        AND (actual_dep_utc IS NULL OR actual_arr_utc IS NULL)
                       THEN 'missing_actual_times'
                   WHEN clock_checked AND _clock_bad THEN 'clock_time_mismatch'
                   ELSE 'ok'
               END AS quality_flag
        FROM j
        """
    )
    report = QualityReport(clock_mismatch_max_share=max_share)
    rows = con.execute(
        f"""
        SELECT strftime(service_date, '%Y-%m') AS month,
               count(*) AS rows,
               count(*) FILTER (WHERE quality_flag = 'duplicate') AS duplicate,
               count(*) FILTER (WHERE quality_flag = 'conflicting_duplicate')
                   AS conflicting_duplicate,
               count(*) FILTER (WHERE quality_flag = 'missing_actual_times')
                   AS missing_actual_times,
               count(*) FILTER (WHERE quality_flag = 'clock_time_mismatch')
                   AS clock_time_mismatch,
               count(*) FILTER (WHERE cancelled) AS cancelled,
               count(*) FILTER (WHERE diverted) AS diverted,
               count(*) FILTER (WHERE clock_checked) AS clock_checked,
               count(*) FILTER (WHERE sched_arr_check_min IS DISTINCT FROM sched_arr_local_min)
                   AS sched_arr_mismatch
        FROM {target} GROUP BY 1 ORDER BY 1
        """
    ).fetchall()
    for month, *counts in rows:
        names = (
            "rows",
            *FLAG_NAMES[:2],
            "missing_actual_times",
            "clock_time_mismatch",
            "cancelled",
            "diverted",
        )
        report.by_month[month] = {n: int(c) for n, c in zip(names, counts[:7], strict=True)}
        report.clock_checked += int(counts[7])
        report.sched_arr_mismatch += int(counts[8])
    report.clock_mismatch = report.totals().get("clock_time_mismatch", 0)
    if report.clock_mismatch_share > max_share:
        raise QualityError(
            f"clock-time mismatch share {report.clock_mismatch_share:.4%} exceeds the limit "
            f"{max_share:.4%} ({report.clock_mismatch} of {report.clock_checked} flights): the "
            "computed instants disagree with BTS DepTime/ArrTime, so the time model is suspect",
            report,
        )
    return report
