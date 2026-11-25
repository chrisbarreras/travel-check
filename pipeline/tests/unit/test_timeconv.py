"""UTC instant computation (ADR-0008, research R3)."""

import datetime as dt
from collections.abc import Sequence
from zoneinfo import ZoneInfo

import duckdb
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from flight_pipeline.prepare.timeconv import (
    add_instants,
    build_offset_tables,
    hhmm_minutes,
    local_minute_of_day,
    local_to_utc,
)

UTC = dt.UTC
ZONES = [
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Phoenix",
    "America/Los_Angeles",
    "America/Anchorage",
    "Pacific/Honolulu",
    "America/Puerto_Rico",
    "Pacific/Guam",
]
START, END = dt.date(2025, 10, 1), dt.date(2026, 9, 30)


@pytest.mark.parametrize(
    ("value", "minutes"),
    [("0800", 480), ("0000", 0), ("2400", 1440), ("0030", 30), ("5", 5), ("1359", 839), (930, 570)],
)
def test_hhmm_minutes(value: str | int, minutes: int) -> None:
    assert hhmm_minutes(value) == minutes


@pytest.mark.parametrize("value", ["2401", "0960", "abc", "", "-100"])
def test_hhmm_minutes_rejects_invalid(value: str) -> None:
    with pytest.raises(ValueError, match="HHMM"):
        hhmm_minutes(value)


def test_local_minute_of_day_maps_2400_to_midnight() -> None:
    assert local_minute_of_day("2400") == 0
    assert local_minute_of_day("0815") == 495


def u(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s).replace(tzinfo=UTC)


@pytest.mark.parametrize(
    ("date", "hhmm", "tz", "expected"),
    [
        (dt.date(2026, 1, 5), "0800", "America/New_York", "2026-01-05T13:00"),
        (dt.date(2026, 1, 7), "2400", "America/Phoenix", "2026-01-08T07:00"),
        (dt.date(2026, 1, 8), "0000", "America/Phoenix", "2026-01-08T07:00"),
        (dt.date(2026, 7, 1), "0800", "America/Chicago", "2026-07-01T13:00"),  # CDT
        (dt.date(2026, 7, 1), "0800", "America/Phoenix", "2026-07-01T15:00"),  # no DST
        # Spring forward: 02:30 does not exist in Chicago; fold=0 uses the earlier offset (CST)
        (dt.date(2026, 3, 8), "0230", "America/Chicago", "2026-03-08T08:30"),
        (dt.date(2026, 3, 8), "0320", "America/Chicago", "2026-03-08T08:20"),
        # Fall back: 01:30 happens twice; fold=0 takes the first occurrence (CDT)
        (dt.date(2025, 11, 2), "0130", "America/Chicago", "2025-11-02T06:30"),
        (dt.date(2025, 11, 2), "0210", "America/Chicago", "2025-11-02T08:10"),
    ],
)
def test_local_to_utc(date: dt.date, hhmm: str, tz: str, expected: str) -> None:
    assert local_to_utc(date, hhmm_minutes(hhmm), tz) == u(expected)


def run_instants(
    con: duckdb.DuckDBPyConnection,
    rows: Sequence[tuple[dt.date, int, int, int | None, int | None, str]],
) -> list[tuple[dt.datetime, dt.datetime, dt.datetime | None, dt.datetime | None]]:
    con.execute(
        "CREATE OR REPLACE TABLE src (service_date DATE, crs_dep_min INTEGER, "
        "sched_elapsed_min INTEGER, dep_delay_min INTEGER, actual_elapsed_min INTEGER, "
        "origin_tz VARCHAR, rid INTEGER)"
    )
    con.executemany(
        "INSERT INTO src VALUES (?, ?, ?, ?, ?, ?, ?)", [(*r, i) for i, r in enumerate(rows)]
    )
    add_instants(con, "src", "out")
    return [
        tuple(None if v is None else v.replace(tzinfo=UTC) for v in row)  # type: ignore[misc]
        for row in con.execute(
            "SELECT sched_dep_utc, sched_arr_utc, actual_dep_utc, actual_arr_utc "
            "FROM out ORDER BY rid"
        ).fetchall()
    ]


@pytest.fixture(scope="module")
def con() -> duckdb.DuckDBPyConnection:
    c = duckdb.connect()
    build_offset_tables(c, ZONES, START, END)
    return c


def test_instants_from_offsets(con: duckdb.DuckDBPyConnection) -> None:
    rows = [
        # Inbound d3: +40 delay, 85 min block
        (dt.date(2026, 1, 7), 480, 80, 40, 85, "America/New_York"),
        # Midnight: 22:00 ET departure, +95 delay, arrives after local midnight
        (dt.date(2026, 1, 6), 1320, 85, 95, 85, "America/New_York"),
        # Cancelled: no actual times
        (dt.date(2026, 1, 8), 480, 80, None, None, "America/New_York"),
        # Diverted: departed, no arrival
        (dt.date(2026, 1, 10), 480, 80, 10, None, "America/New_York"),
        # 2400 scheduled departure
        (dt.date(2026, 1, 7), 1440, 75, 0, 75, "America/Phoenix"),
        # Early departure (negative delay)
        (dt.date(2026, 1, 5), 480, 80, -6, 77, "America/New_York"),
    ]
    out = run_instants(con, rows)
    assert out[0] == (
        u("2026-01-07T13:00"),
        u("2026-01-07T14:20"),
        u("2026-01-07T13:40"),
        u("2026-01-07T15:05"),
    )
    assert out[1] == (
        u("2026-01-07T03:00"),
        u("2026-01-07T04:25"),
        u("2026-01-07T04:35"),
        u("2026-01-07T06:00"),
    )
    assert out[2] == (u("2026-01-08T13:00"), u("2026-01-08T14:20"), None, None)
    assert out[3] == (u("2026-01-10T13:00"), u("2026-01-10T14:20"), u("2026-01-10T13:10"), None)
    assert out[4][0] == u("2026-01-08T07:00")
    assert out[5][2:] == (u("2026-01-05T12:54"), u("2026-01-05T14:11"))


def test_dst_slack_is_true_elapsed_time(con: duckdb.DuckDBPyConnection) -> None:
    spring_in, spring_out, fall_in, fall_out = run_instants(
        con,
        [
            (dt.date(2026, 3, 8), 90, 80, 0, 80, "America/New_York"),  # WN101 01:30 ET
            (dt.date(2026, 3, 8), 200, 120, 0, 120, "America/Chicago"),  # WN102 03:20 CDT
            (dt.date(2025, 11, 2), 30, 80, 0, 80, "America/New_York"),  # WN201 00:30 EDT
            (dt.date(2025, 11, 2), 130, 120, 0, 120, "America/Chicago"),  # WN202 02:10 CST
        ],
    )
    assert spring_out[2] is not None
    assert spring_in[3] is not None
    assert fall_out[2] is not None
    assert fall_in[3] is not None
    assert spring_out[2] - spring_in[3] == dt.timedelta(minutes=30)  # naive local: 90
    assert fall_out[2] - fall_in[3] == dt.timedelta(minutes=140)  # naive local: 80


def test_results_do_not_depend_on_session_time_zone() -> None:
    rows = [
        (dt.date(2026, 3, 8), 200, 120, 0, 120, "America/Chicago"),
        (dt.date(2025, 11, 2), 90, 80, 0, 80, "America/Chicago"),
    ]
    results = []
    for session_tz in ("UTC", "Asia/Tokyo", "America/Los_Angeles"):
        c = duckdb.connect()
        c.execute(f"SET TimeZone = '{session_tz}'")
        build_offset_tables(c, ZONES, START, END)
        results.append(run_instants(c, rows))
    assert results[0] == results[1] == results[2]


@settings(max_examples=150)
@given(
    day=st.dates(min_value=START, max_value=END),
    minutes=st.integers(min_value=0, max_value=1440),
    tz=st.sampled_from(ZONES),
)
def test_sql_conversion_matches_zoneinfo(
    con: duckdb.DuckDBPyConnection, day: dt.date, minutes: int, tz: str
) -> None:
    [(sched_dep, *_)] = run_instants(con, [(day, minutes, 60, 0, 60, tz)])
    assert sched_dep == local_to_utc(day, minutes, tz)
    local = dt.datetime.combine(day, dt.time()) + dt.timedelta(minutes=minutes)
    assert sched_dep == local.replace(tzinfo=ZoneInfo(tz), fold=0).astimezone(UTC)


@settings(max_examples=100)
@given(
    day=st.dates(min_value=START, max_value=END),
    minutes=st.integers(min_value=0, max_value=1440),
    sched_elapsed=st.integers(min_value=20, max_value=700),
    delay=st.integers(min_value=-30, max_value=1500),
    elapsed=st.integers(min_value=15, max_value=800),
    tz=st.sampled_from(ZONES),
)
def test_actual_arrival_minus_departure_equals_elapsed(
    con: duckdb.DuckDBPyConnection,
    day: dt.date,
    minutes: int,
    sched_elapsed: int,
    delay: int,
    elapsed: int,
    tz: str,
) -> None:
    [(sdep, sarr, adep, aarr)] = run_instants(
        con, [(day, minutes, sched_elapsed, delay, elapsed, tz)]
    )
    assert adep is not None
    assert aarr is not None
    assert aarr - adep == dt.timedelta(minutes=elapsed)
    assert sarr - sdep == dt.timedelta(minutes=sched_elapsed)
    assert adep - sdep == dt.timedelta(minutes=delay)


def test_offset_tables_cover_utc_to_local(con: duckdb.DuckDBPyConnection) -> None:
    # 2026-03-08 08:00 UTC is exactly when Chicago switches to CDT
    assert local_minute_of_day_sql(con, "2026-03-08 07:59", "America/Chicago") == 119
    assert local_minute_of_day_sql(con, "2026-03-08 08:00", "America/Chicago") == 180
    assert local_minute_of_day_sql(con, "2026-01-06 06:00", "America/Chicago") == 0


def local_minute_of_day_sql(con: duckdb.DuckDBPyConnection, utc: str, tz: str) -> int:
    row = con.execute(
        "SELECT CAST(extract('hour' FROM t.u + to_minutes(o.offset_min)) * 60 "
        "+ extract('minute' FROM t.u + to_minutes(o.offset_min)) AS INTEGER) "
        "FROM (SELECT CAST(? AS TIMESTAMP) AS u, ? AS tz) t "
        "JOIN tz_utc_offsets o ON o.tz = t.tz AND t.u >= o.utc_start AND t.u < o.utc_end",
        [utc, tz],
    ).fetchone()
    assert row is not None
    return int(row[0])
