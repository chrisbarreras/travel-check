"""Sold routings from DB1B Market (FR-013a, research R10).

A DB1B Market row is one directional trip of a sampled ticket (a 10% sample). A row with
``MktCoupons = 2`` is a trip with exactly one connection: ``AirportGroup`` is
``ORIGIN:HUB:DEST`` and ``TkCarrierGroup`` is the selling airline of each leg, for example
``AA:AS``. Rows are aggregated per file and summed over the period's quarters. Legs whose
selling airline is not recorded (``--``) are not counted; their passenger share is reported.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb

from flight_pipeline.prepare.normalize import HeaderError
from flight_pipeline.providers.bts_ontime import extract_single_csv

REQUIRED_COLUMNS = ("MktCoupons", "Year", "Quarter", "AirportGroup", "TkCarrierGroup", "Passengers")
UNKNOWN = "--"


@dataclass(frozen=True)
class Db1bReport:
    quarters: list[str]
    two_coupon_passengers: int
    unknown_airline_passengers: int

    @property
    def unknown_airline_share(self) -> float:
        if self.two_coupon_passengers == 0:
            return 0.0
        return round(self.unknown_airline_passengers / self.two_coupon_passengers, 6)

    def to_json(self) -> dict[str, Any]:
        return {
            "quarters": self.quarters,
            "two_coupon_passengers": self.two_coupon_passengers,
            "unknown_airline_passengers": self.unknown_airline_passengers,
            "unknown_airline_share": self.unknown_airline_share,
        }


def _csv(path: Path) -> str:
    p = str(path).replace("'", "''")
    return f"read_csv('{p}', all_varchar = true, header = true)"


def _aggregate_file(con: duckdb.DuckDBPyConnection, path: Path, table: str) -> None:
    """2-coupon routings of one file: (year, quarter, airports, carriers, passengers)."""
    cols = {
        str(row[0]).strip()
        for row in con.execute(f"DESCRIBE SELECT * FROM {_csv(path)}").fetchall()
    }
    missing = sorted(c for c in REQUIRED_COLUMNS if c not in cols)
    if missing:
        raise HeaderError(path, missing)
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE {table} AS
        SELECT CAST(Year AS INTEGER) AS year,
               CAST(Quarter AS INTEGER) AS quarter,
               string_split(AirportGroup, ':') AS airports,
               string_split(TkCarrierGroup, ':') AS carriers,
               sum(CAST(Passengers AS DOUBLE)) AS passengers
        FROM {_csv(path)}
        WHERE CAST(CAST(MktCoupons AS DOUBLE) AS INTEGER) = 2
        GROUP BY ALL
        """
    )


def _combine(
    con: duckdb.DuckDBPyConnection,
    tables: Sequence[str],
    carrier_map: Mapping[str, str],
    target: str,
) -> Db1bReport:
    con.execute("CREATE OR REPLACE TEMP TABLE _carrier_map (code VARCHAR, mapped VARCHAR)")
    if carrier_map:
        con.executemany("INSERT INTO _carrier_map VALUES (?, ?)", sorted(carrier_map.items()))
    union = " UNION ALL ".join(f"SELECT * FROM {t}" for t in tables)
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _db1b_all AS
        SELECT year, quarter, airports[1] AS origin, airports[2] AS hub, airports[3] AS dest,
               coalesce(m1.mapped, carriers[1]) AS airline_in,
               coalesce(m2.mapped, carriers[2]) AS airline_out,
               passengers
        FROM ({union}) r
        LEFT JOIN _carrier_map m1 ON m1.code = r.carriers[1]
        LEFT JOIN _carrier_map m2 ON m2.code = r.carriers[2]
        WHERE len(r.airports) = 3 AND len(r.carriers) = 2
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TABLE {target} AS
        SELECT origin, hub, dest, airline_in, airline_out,
               CAST(round(sum(passengers)) AS INTEGER) AS passengers
        FROM _db1b_all
        WHERE airline_in <> '{UNKNOWN}' AND airline_out <> '{UNKNOWN}'
        GROUP BY ALL
        ORDER BY origin, hub, dest, airline_in, airline_out
        """
    )
    total, unknown = con.execute(
        f"""
        SELECT CAST(round(coalesce(sum(passengers), 0)) AS BIGINT),
               CAST(round(coalesce(sum(passengers) FILTER (
                   WHERE airline_in = '{UNKNOWN}' OR airline_out = '{UNKNOWN}'), 0)) AS BIGINT)
        FROM _db1b_all
        """
    ).fetchone() or (0, 0)
    quarters = [
        f"{y}-{q}"
        for y, q in con.execute(
            "SELECT DISTINCT year, quarter FROM _db1b_all ORDER BY 1, 2"
        ).fetchall()
    ]
    for t in [*tables, "_db1b_all"]:
        con.execute(f"DROP TABLE IF EXISTS {t}")
    return Db1bReport(quarters, int(total), int(unknown))


def load_sold_routings(
    con: duckdb.DuckDBPyConnection,
    csvs: Sequence[Path],
    carrier_map: Mapping[str, str],
    target: str,
) -> Db1bReport:
    """Create ``target`` (SoldRouting rows) from DB1B Market CSV files."""
    tables: list[str] = []
    for i, path in enumerate(csvs):
        _aggregate_file(con, path, f"_db1b_{i}")
        tables.append(f"_db1b_{i}")
    return _combine(con, tables, carrier_map, target)


def prepare_sold_routings(
    con: duckdb.DuckDBPyConnection,
    zips: Sequence[tuple[str, Path]],
    carrier_map: Mapping[str, str],
    work_dir: Path,
    target: str,
) -> Db1bReport:
    """Create ``target`` from quarterly DB1B Market zips ``(quarter key, path)``. Each
    quarter's CSV is extracted into ``work_dir``, aggregated and deleted before the next one,
    so only one extracted file is on disk at a time."""
    work_dir.mkdir(parents=True, exist_ok=True)
    tables: list[str] = []
    for i, (key, zip_path) in enumerate(zips):
        csv_path = work_dir / f"{key}.csv"
        try:
            extract_single_csv(zip_path, csv_path)
            _aggregate_file(con, csv_path, f"_db1b_{i}")
        finally:
            csv_path.unlink(missing_ok=True)
        tables.append(f"_db1b_{i}")
    return _combine(con, tables, carrier_map, target)


def unmapped_airlines(
    con: duckdb.DuckDBPyConnection, sold: str, flights: str
) -> tuple[dict[str, int], int]:
    """Selling-airline codes in ``sold`` (after ``carrier_map``) that are not marketing
    airlines in ``flights``: sampled passengers per code, and the passengers on routings
    with at least one such leg (each routing counted once). These routings can never match
    an itinerary, so they are reported rather than dropped silently (spec edge case)."""
    con.execute(
        f"CREATE OR REPLACE TEMP TABLE _mkt AS SELECT DISTINCT marketing_airline AS code "
        f"FROM {flights}"
    )
    per_code = {
        str(code): int(pax)
        for code, pax in con.execute(
            f"""
            SELECT code, CAST(sum(passengers) AS BIGINT) FROM (
                SELECT airline_in AS code, passengers FROM {sold}
                UNION ALL
                SELECT airline_out, passengers FROM {sold} WHERE airline_out <> airline_in
            )
            WHERE code NOT IN (SELECT code FROM _mkt)
            GROUP BY code ORDER BY 2 DESC, 1
            """
        ).fetchall()
    }
    row = con.execute(
        f"""
        SELECT CAST(coalesce(sum(passengers), 0) AS BIGINT) FROM {sold}
        WHERE airline_in NOT IN (SELECT code FROM _mkt)
           OR airline_out NOT IN (SELECT code FROM _mkt)
        """
    ).fetchone()
    con.execute("DROP TABLE IF EXISTS _mkt")
    return per_code, int(row[0]) if row else 0
