"""Sold routings from DB1B Market (FR-013a, research R10)."""

import json
import zipfile
from pathlib import Path

import duckdb
import pytest

from flight_pipeline.models import SoldRouting, validate_table
from flight_pipeline.prepare.db1b import Db1bReport, prepare_sold_routings
from flight_pipeline.prepare.normalize import HeaderError

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
SAMPLE = FIXTURES / "db1b_sample.csv"
EXPECTED = json.loads((FIXTURES / "expected" / "sold_routings.json").read_text(encoding="utf-8"))


def quarter_zips(tmp_path: Path) -> list[tuple[str, Path]]:
    """The fixture split into one zip per quarter, as BTS publishes it."""
    lines = SAMPLE.read_text(encoding="utf-8").splitlines()
    header = lines[0].split(",")
    year, quarter = header.index("Year"), header.index("Quarter")
    by_key: dict[str, list[str]] = {}
    for line in lines[1:]:
        cols = line.split(",")
        by_key.setdefault(f"{cols[year]}-{cols[quarter]}", []).append(line)
    out: list[tuple[str, Path]] = []
    for key in sorted(by_key):
        path = tmp_path / "db1b" / f"{key}.zip"
        path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f"Market_{key}.csv", "\n".join([lines[0], *by_key[key]]) + "\n")
            zf.writestr("readme.html", "<html></html>")
        out.append((key, path))
    return out


def run(
    tmp_path: Path, carrier_map: dict[str, str] | None = None
) -> tuple[duckdb.DuckDBPyConnection, Db1bReport]:
    con = duckdb.connect()
    report = prepare_sold_routings(
        con, quarter_zips(tmp_path), carrier_map or {}, tmp_path / "work", "sold_routings"
    )
    return con, report


def rows(con: duckdb.DuckDBPyConnection) -> list[list[object]]:
    return [
        list(r)
        for r in con.execute(
            "SELECT origin, hub, dest, airline_in, airline_out, passengers FROM sold_routings "
            "ORDER BY ALL"
        ).fetchall()
    ]


def test_two_coupon_routings_summed_over_quarters(tmp_path: Path) -> None:
    con, _ = run(tmp_path)
    assert rows(con) == EXPECTED["sold_routings"]


def test_table_matches_model(tmp_path: Path) -> None:
    con, _ = run(tmp_path)
    assert validate_table(con, "sold_routings", SoldRouting) == len(EXPECTED["sold_routings"])


def test_unknown_airline_legs_excluded_and_share_reported(tmp_path: Path) -> None:
    con, report = run(tmp_path)
    assert con.execute(
        "SELECT count(*) FROM sold_routings WHERE '--' IN (airline_in, airline_out)"
    ).fetchone() == (0,)
    assert report.quarters == EXPECTED["quarters"]
    assert report.two_coupon_passengers == EXPECTED["two_coupon_passengers"]
    assert report.unknown_airline_passengers == EXPECTED["unknown_airline_passengers"]
    assert report.unknown_airline_share == EXPECTED["unknown_airline_share"]
    data = report.to_json()
    assert data["unknown_airline_share"] == EXPECTED["unknown_airline_share"]
    assert data["quarters"] == EXPECTED["quarters"]


def test_one_and_three_coupon_rows_ignored(tmp_path: Path) -> None:
    con, _ = run(tmp_path)
    # The 3-coupon CMH:ORD:DEN:SAN row would otherwise add 50 to CMH:ORD:DEN AA:AA.
    assert con.execute(
        "SELECT passengers FROM sold_routings WHERE origin = 'CMH' AND hub = 'ORD' "
        "AND dest = 'DEN' AND airline_in = 'AA'"
    ).fetchone() == (12,)


def test_carrier_map_applied(tmp_path: Path) -> None:
    con, _ = run(tmp_path, {"US": "AA"})
    assert rows(con) == EXPECTED["with_carrier_map_US_to_AA"]


def test_extracted_csv_deleted_and_zip_kept(tmp_path: Path) -> None:
    run(tmp_path)
    assert list((tmp_path / "work").glob("*.csv")) == []
    assert sorted(p.name for p in (tmp_path / "db1b").iterdir()) == ["2025-4.zip", "2026-1.zip"]


def test_missing_columns_fail(tmp_path: Path) -> None:
    path = tmp_path / "bad.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("Market.csv", "Year,Quarter,Passengers\n2026,1,1.00\n")
    with pytest.raises(HeaderError, match="AirportGroup"):
        prepare_sold_routings(duckdb.connect(), [("2026-1", path)], {}, tmp_path / "w", "s")


def test_unmapped_selling_airlines_reported(tmp_path: Path) -> None:
    from flight_pipeline.prepare.db1b import unmapped_airlines
    from flight_pipeline.prepare.normalize import normalize_ontime
    from flight_pipeline.providers.timezones import AirportsDataTimezones

    for mapping, expected in (({}, ({"US": 4}, 4)), ({"US": "AA"}, ({}, 0))):
        con, _ = run(tmp_path / str(len(mapping)), mapping)
        normalize_ontime(
            con,
            [FIXTURES / "ontime_sample.csv"],
            AirportsDataTimezones({}),
            clock_mismatch_max_share=0.2,
        )
        # US is not a marketing airline in the on-time sample (AA, AS, DL, UA, WN)
        assert unmapped_airlines(con, "sold_routings", "flights") == expected
