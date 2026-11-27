"""Raw BTS CSV -> typed FlightRecord table (FR-003, FR-005, FR-007)."""

import datetime as dt
import json
from pathlib import Path
from typing import Any

import duckdb
import pytest

from flight_pipeline.models import FlightRecord, validate_table
from flight_pipeline.prepare.normalize import (
    REQUIRED_COLUMNS,
    HeaderError,
    normalize_ontime,
)
from flight_pipeline.providers.timezones import AirportsDataTimezones

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
SAMPLE = FIXTURES / "ontime_sample.csv"
UTC = dt.UTC


def run(tmp_path: Path, csv_paths: list[Path] | None = None) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    normalize_ontime(
        con,
        csv_paths or [SAMPLE],
        AirportsDataTimezones({}),
        clock_mismatch_max_share=0.2,
        target="flights",
        case_column="FixtureCase",
    )
    return con


def by_case(con: duckdb.DuckDBPyConnection) -> dict[str, dict[str, Any]]:
    cur = con.execute("SELECT * FROM flights_with_case")
    cols = [d[0] for d in cur.description or []]
    return {r[cols.index("fixture_case")]: dict(zip(cols, r, strict=True)) for r in cur.fetchall()}


def iso(v: dt.datetime | None) -> str | None:
    return None if v is None else v.strftime("%Y-%m-%dT%H:%M")


def test_table_matches_flight_record_model(tmp_path: Path) -> None:
    con = run(tmp_path)
    assert validate_table(con, "flights", FlightRecord) == 222


def test_instants_match_hand_computed_values(tmp_path: Path) -> None:
    expected = json.loads((FIXTURES / "expected" / "timeconv.json").read_text())
    rows = by_case(run(tmp_path))
    for case, exp in expected.items():
        if case.startswith("_"):
            continue
        row = rows[case]
        assert iso(row["sched_dep_utc"]) == exp["sched_dep"], case
        assert iso(row["sched_arr_utc"]) == exp["sched_arr"], case
        assert iso(row["actual_dep_utc"]) == exp["actual_dep"], case
        assert iso(row["actual_arr_utc"]) == exp["actual_arr"], case
        for key in ("sched_dep_local_min", "sched_arr_local_min"):
            if key in exp:
                assert row[key] == exp[key], (case, key)


def test_fields_typed_from_raw(tmp_path: Path) -> None:
    rows = by_case(run(tmp_path))
    r = rows["i1_in_d1"]
    assert r["marketing_airline"] == "AA"
    assert r["operating_airline"] == "MQ"  # from the 'Operating_Airline ' column
    assert r["flight_number"] == 3100
    assert r["service_date"] == dt.date(2026, 1, 5)
    assert (r["origin"], r["dest"]) == ("CMH", "ORD")
    assert r["sched_elapsed_min"] == 80
    assert r["cancelled"] is False
    assert r["cancellation_code"] is None
    c = rows["i1_in_d4"]
    assert c["cancelled"] is True
    assert c["cancellation_code"] == "B"
    assert rows["i1_in_d6"]["diverted"] is True
    assert rows["i1_in_d8"]["weather_delay_min"] == 120


def test_weather_flag_uses_weather_delay_or_weather_cancellation_only(tmp_path: Path) -> None:
    expected = json.loads((FIXTURES / "expected" / "quality.json").read_text())
    rows = by_case(run(tmp_path))
    flagged = sorted(case for case, r in rows.items() if r["weather_affected"])
    assert flagged == expected["weather_affected"]
    assert rows["i1_in_d2"]["weather_affected"] is False  # NAS delay only
    assert rows["i1_out_d5"]["weather_affected"] is False  # cancelled, carrier (A)


def test_missing_required_column_lists_names(tmp_path: Path) -> None:
    text = SAMPLE.read_text().splitlines()
    header = text[0].replace("WeatherDelay", "WxDelay").replace("CRSDepTime", "CRS_Dep")
    bad = tmp_path / "bad.csv"
    bad.write_text("\n".join([header, *text[1:]]) + "\n")
    with pytest.raises(HeaderError) as excinfo:
        run(tmp_path, [bad])
    assert excinfo.value.missing == ["CRSDepTime", "WeatherDelay"]
    assert "CRSDepTime" in str(excinfo.value)


def test_required_columns_cover_research_r1() -> None:
    assert set(REQUIRED_COLUMNS) >= {
        "Marketing_Airline_Network",
        "Operating_Airline",
        "Flight_Number_Marketing_Airline",
        "FlightDate",
        "Origin",
        "Dest",
        "CRSDepTime",
        "CRSArrTime",
        "DepTime",
        "ArrTime",
        "DepDelay",
        "CRSElapsedTime",
        "ActualElapsedTime",
        "Cancelled",
        "CancellationCode",
        "Diverted",
        "WeatherDelay",
    }


def test_missing_time_zone_stops_with_list(tmp_path: Path) -> None:
    from flight_pipeline.providers.timezones import MissingTimezoneError

    text = SAMPLE.read_text().replace(",PHX,SAN,", ",QQZ,SAN,")
    path = tmp_path / "s.csv"
    path.write_text(text)
    with pytest.raises(MissingTimezoneError, match="QQZ"):
        run(tmp_path, [path])


def test_multiple_monthly_files_are_combined(tmp_path: Path) -> None:
    lines = SAMPLE.read_text().splitlines()
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    a.write_text("\n".join(lines[:60]) + "\n")
    b.write_text("\n".join([lines[0], *lines[60:]]) + "\n")
    con = run(tmp_path, [a, b])
    row = con.execute("SELECT count(*) FROM flights").fetchone()
    assert row == (222,)
