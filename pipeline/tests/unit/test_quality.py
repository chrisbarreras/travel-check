"""Data-quality flags and the clock-time consistency check (FR-005, research R3)."""

import json
from pathlib import Path

import duckdb
import pytest

from flight_pipeline.prepare.normalize import normalize_ontime
from flight_pipeline.prepare.quality import QualityError, QualityReport
from flight_pipeline.providers.timezones import AirportsDataTimezones

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
SAMPLE = FIXTURES / "ontime_sample.csv"
EXPECTED = json.loads((FIXTURES / "expected" / "quality.json").read_text())


def run(
    max_share: float = 0.2, path: Path = SAMPLE
) -> tuple[duckdb.DuckDBPyConnection, QualityReport]:
    con = duckdb.connect()
    report = normalize_ontime(
        con,
        [path],
        AirportsDataTimezones({}),
        clock_mismatch_max_share=max_share,
        target="flights",
        case_column="FixtureCase",
    )
    return con, report


def flags(con: duckdb.DuckDBPyConnection) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for flag, case in con.execute(
        "SELECT quality_flag, fixture_case FROM flights_with_case WHERE quality_flag <> 'ok' "
        "ORDER BY fixture_case"
    ).fetchall():
        out.setdefault(flag, []).append(case)
    return out


def test_flags_match_expected_cases() -> None:
    con, _ = run()
    assert flags(con) == EXPECTED["flags"]


def test_identical_duplicate_keeps_one_ok_copy() -> None:
    con, _ = run()
    rows = con.execute(
        "SELECT quality_flag, count(*) FROM flights_with_case WHERE fixture_case = 'i1_out_d9' "
        "GROUP BY 1 ORDER BY 1"
    ).fetchall()
    assert rows == [("duplicate", 1), ("ok", 1)]


def test_ok_rows_have_unique_identity() -> None:
    con, _ = run()
    dup = con.execute(
        "SELECT count(*) FROM (SELECT marketing_airline, flight_number, service_date, origin "
        "FROM flights WHERE quality_flag = 'ok' GROUP BY ALL HAVING count(*) > 1)"
    ).fetchone()
    assert dup == (0,)


def test_report_counts() -> None:
    _, report = run()
    totals = report.totals()
    for name, count in EXPECTED["counts"].items():
        assert totals[name] == count, name
    assert totals["rows"] == EXPECTED["rows_read"]
    assert totals["cancelled"] == EXPECTED["cancelled"]
    assert totals["diverted"] == EXPECTED["diverted"]


def test_report_by_month_and_json() -> None:
    _, report = run()
    data = report.to_json()
    assert set(data["by_month"]) == {"2025-11", "2026-01", "2026-03"}
    assert data["by_month"]["2026-01"]["clock_time_mismatch"] == 1
    assert data["totals"]["rows"] == 222
    assert 0 < data["clock_mismatch_share"] < 0.02
    assert data["clock_mismatch_max_share"] == 0.2
    assert data["sched_arr_mismatch"] == 0


def test_clock_mismatch_share_above_threshold_fails() -> None:
    # 1 mismatch among the checked flights is above a 0.1% limit
    with pytest.raises(QualityError, match="clock"):
        run(max_share=0.001)


def test_clock_check_uses_2400_as_midnight() -> None:
    con, _ = run()
    flag = con.execute(
        "SELECT quality_flag FROM flights_with_case WHERE fixture_case = 'aa2200_d2'"
    ).fetchone()
    assert flag == ("ok",)  # ArrTime 2400 matches the computed 00:00 local arrival


def test_rows_with_invalid_schedule_are_dropped_and_counted(tmp_path: Path) -> None:
    lines = SAMPLE.read_text().splitlines()
    header = lines[0].split(",")
    elapsed = header.index("CRSElapsedTime")
    bad = []
    for value in ("-60.00", ""):
        row = lines[1].split(",")
        row[elapsed] = value
        row[header.index("Flight_Number_Marketing_Airline")] = "9999" if value else "9998"
        bad.append(",".join(row))
    path = tmp_path / "s.csv"
    path.write_text("\n".join([*lines, *bad]) + "\n")
    con, report = run(path=path)
    assert report.totals()["invalid_schedule"] == 2
    assert report.totals()["rows"] == 222
    assert report.to_json()["by_month"]["2026-01"]["invalid_schedule"] == 2
    assert con.execute("SELECT count(*) FROM flights WHERE flight_number >= 9998").fetchone() == (
        0,
    )


def test_same_flight_number_on_two_segments_are_distinct_flights() -> None:
    con, _ = run()
    rows = con.execute(
        "SELECT fixture_case, origin, dest, quality_flag FROM flights_with_case "
        "WHERE fixture_case LIKE 'seg_%' ORDER BY 1"
    ).fetchall()
    assert rows == [("seg_1", "CMH", "ORD", "ok"), ("seg_2", "ORD", "DEN", "ok")]


def test_hhmm_with_minutes_of_60_or_more_is_an_invalid_schedule(tmp_path: Path) -> None:
    lines = SAMPLE.read_text().splitlines()
    header = lines[0].split(",")
    row = lines[1].split(",")
    row[header.index("CRSDepTime")] = "1275"
    row[header.index("Flight_Number_Marketing_Airline")] = "9997"
    path = tmp_path / "s.csv"
    path.write_text("\n".join([*lines, ",".join(row)]) + "\n")
    _, report = run(path=path)
    assert report.totals()["invalid_schedule"] == 1
