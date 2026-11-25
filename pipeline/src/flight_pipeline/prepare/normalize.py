"""Raw BTS on-time CSV files -> typed FlightRecord table (FR-003 to FR-005, FR-007)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import duckdb

from flight_pipeline.models import FlightRecord
from flight_pipeline.prepare.quality import QualityError, QualityReport, flag_quality
from flight_pipeline.prepare.timeconv import add_instants, build_offset_tables
from flight_pipeline.providers.base import TimezoneSource

# Research R1. Header names are compared after stripping whitespace, because the real files
# write "Operating_Airline " with a trailing space.
REQUIRED_COLUMNS = (
    "FlightDate",
    "Marketing_Airline_Network",
    "Operating_Airline",
    "Flight_Number_Marketing_Airline",
    "Origin",
    "Dest",
    "CRSDepTime",
    "DepTime",
    "DepDelay",
    "CRSArrTime",
    "ArrTime",
    "Cancelled",
    "CancellationCode",
    "Diverted",
    "CRSElapsedTime",
    "ActualElapsedTime",
    "WeatherDelay",
)


class HeaderError(ValueError):
    """A CSV file lacks required columns (research R1)."""

    def __init__(self, path: Path, missing: list[str]) -> None:
        self.missing = missing
        super().__init__(
            f"{path} is missing required BTS column(s): {', '.join(missing)}. "
            "The BTS file layout may have changed; check research.md R1."
        )


def _quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _csv(path: Path) -> str:
    p = str(path).replace("'", "''")
    return f"read_csv('{p}', all_varchar = true, header = true)"


def _select_for(con: duckdb.DuckDBPyConnection, path: Path, case_column: str | None) -> str:
    cols = [row[0] for row in con.execute(f"DESCRIBE SELECT * FROM {_csv(path)}").fetchall()]
    by_name = {c.strip(): c for c in cols}
    missing = sorted(c for c in REQUIRED_COLUMNS if c not in by_name)
    if missing:
        raise HeaderError(path, missing)
    parts = [f"{_quote(by_name[c])} AS {c}" for c in REQUIRED_COLUMNS]
    if case_column:
        parts.append(f"{_quote(by_name[case_column])} AS fixture_case")
    return f"SELECT {', '.join(parts)} FROM {_csv(path)}"


def _hhmm(col: str) -> str:
    v = f"CAST(trim({col}) AS INTEGER)"
    return (
        f"(CASE WHEN nullif(trim({col}), '') IS NULL THEN NULL "
        f"ELSE ({v} // 100) * 60 + {v} % 100 END)"
    )


def _int(col: str) -> str:
    return f"CAST(round(CAST(nullif(trim({col}), '') AS DOUBLE)) AS INTEGER)"


def _flag(col: str) -> str:
    return f"(CAST(nullif(trim({col}), '') AS DOUBLE) = 1)"


def normalize_ontime(
    con: duckdb.DuckDBPyConnection,
    csv_paths: Sequence[Path],
    timezones: TimezoneSource,
    *,
    clock_mismatch_max_share: float,
    target: str = "flights",
    case_column: str | None = None,
) -> QualityReport:
    """Create ``target`` with exactly the FlightRecord columns (data-model.md), every row of
    the input files kept and flagged. ``case_column`` (tests only) also keeps a raw column in
    ``{target}_with_case`` as ``fixture_case``.

    Raises HeaderError, MissingTimezoneError, ValueError (invalid times) or QualityError."""
    if not csv_paths:
        raise ValueError("no on-time CSV files to normalize")
    selects = [_select_for(con, p, case_column) for p in csv_paths]
    con.execute("CREATE OR REPLACE TEMP TABLE _raw AS " + " UNION ALL BY NAME ".join(selects))
    case = ", fixture_case" if case_column else ""
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _typed AS
        SELECT trim(Marketing_Airline_Network) AS marketing_airline,
               trim(Operating_Airline) AS operating_airline,
               CAST(trim(Flight_Number_Marketing_Airline) AS INTEGER) AS flight_number,
               CAST(trim(FlightDate) AS DATE) AS service_date,
               trim(Origin) AS origin,
               trim(Dest) AS dest,
               coalesce(CAST(trim(CRSDepTime) AS INTEGER) % 100 < 60
                        AND CAST(trim(CRSArrTime) AS INTEGER) % 100 < 60, false)
                   AS crs_dep_hhmm_ok,
               {_hhmm("CRSDepTime")} AS crs_dep_min,
               {_hhmm("CRSArrTime")} % 1440 AS sched_arr_local_min,
               {_int("CRSElapsedTime")} AS sched_elapsed_min,
               {_flag("Cancelled")} AS cancelled,
               {_flag("Diverted")} AS diverted,
               -- data-model.md: actual times are null when cancelled or diverted
               CASE WHEN {_flag("Cancelled")} OR {_flag("Diverted")} THEN NULL
                    ELSE {_int("DepDelay")} END AS dep_delay_min,
               CASE WHEN {_flag("Cancelled")} OR {_flag("Diverted")} THEN NULL
                    ELSE {_int("ActualElapsedTime")} END AS actual_elapsed_min,
               {_hhmm("DepTime")} AS dep_time_min,
               {_hhmm("ArrTime")} AS arr_time_min,
               nullif(trim(CancellationCode), '') AS cancellation_code,
               {_int("WeatherDelay")} AS weather_delay_min
               {case}
        FROM _raw
        """
    )
    # Rows whose schedule cannot be converted (missing or non-positive CRSElapsedTime, bad
    # HHMM values) are corrupt source records: dropped here and counted as invalid_schedule.
    valid = (
        "crs_dep_min IS NOT NULL AND crs_dep_min BETWEEN 0 AND 1440 AND crs_dep_hhmm_ok "
        "AND sched_arr_local_min IS NOT NULL AND sched_elapsed_min IS NOT NULL "
        "AND sched_elapsed_min >= 1 AND service_date IS NOT NULL"
    )
    invalid_by_month = {
        str(m): int(n)
        for m, n in con.execute(
            "SELECT coalesce(strftime(service_date, '%Y-%m'), 'unknown'), count(*) "
            f"FROM _typed WHERE NOT coalesce({valid}, false) GROUP BY 1"
        ).fetchall()
    }
    con.execute(f"DELETE FROM _typed WHERE NOT coalesce({valid}, false)")

    airports = [
        r[0]
        for r in con.execute(
            "SELECT DISTINCT origin FROM _typed UNION SELECT DISTINCT dest FROM _typed"
        ).fetchall()
    ]
    lookup = timezones.lookup(airports)
    con.execute("CREATE OR REPLACE TEMP TABLE _airport_tz (code VARCHAR, tz VARCHAR)")
    con.executemany(
        "INSERT INTO _airport_tz VALUES (?, ?)", [(c, e.tz) for c, e in sorted(lookup.items())]
    )
    span = con.execute("SELECT min(service_date), max(service_date) FROM _typed").fetchone()
    assert span is not None
    build_offset_tables(con, {e.tz for e in lookup.values()}, span[0], span[1])

    con.execute(
        """
        CREATE OR REPLACE TEMP TABLE _with_tz AS
        SELECT t.*, o.tz AS origin_tz, d.tz AS dest_tz
        FROM _typed t
        JOIN _airport_tz o ON o.code = t.origin
        JOIN _airport_tz d ON d.code = t.dest
        """
    )
    add_instants(con, "_with_tz", "_instants")
    try:
        report = flag_quality(con, "_instants", "_flagged", clock_mismatch_max_share)
    except QualityError as exc:
        exc.report.add_invalid_schedule(invalid_by_month)
        raise
    report.add_invalid_schedule(invalid_by_month)
    _finish(con, target, case_column)
    return report


def _finish(con: duckdb.DuckDBPyConnection, target: str, case_column: str | None) -> None:
    cols = list(FlightRecord.model_fields)
    exprs = {
        "sched_dep_local_min": "crs_dep_min % 1440 AS sched_dep_local_min",
        "weather_affected": (
            "(coalesce(weather_delay_min, 0) > 0 OR coalesce(cancellation_code, '') = 'B') "
            "AS weather_affected"
        ),
    }
    select = ", ".join(exprs.get(c, c) for c in cols)
    con.execute(f"CREATE OR REPLACE TABLE {target} AS SELECT {select} FROM _flagged")
    if case_column:
        con.execute(
            f"CREATE OR REPLACE TABLE {target}_with_case AS "
            f"SELECT {select}, fixture_case FROM _flagged"
        )
