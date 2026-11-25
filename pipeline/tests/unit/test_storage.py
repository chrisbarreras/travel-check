"""Deterministic Parquet output and model tables (research R8)."""

import datetime as dt
from pathlib import Path

import duckdb

from flight_pipeline.models import FlightNumberShare, HubCandidate, ScheduleSlot, SeasonShares
from flight_pipeline.storage import models_to_table, table_hash, write_table


def candidate(code: str, score: float) -> HubCandidate:
    return HubCandidate(
        airport=code,
        departures=10,
        airline_count=2,
        airlines=["AA", "UA"],
        passengers=None,
        weather_share=0.1234567891,
        weather_share_by_season=SeasonShares(winter=0.2, spring=None, summer=0.1, autumn=0.0),
        weather_peak_season="winter",
        eligible_itineraries=3,
        eligible=True,
        score=score,
        rank=1,
    )


def test_models_round_trip_through_parquet(tmp_path: Path) -> None:
    con = duckdb.connect()
    models_to_table(con, "c", HubCandidate, [candidate("ORD", 1.0), candidate("DEN", 0.5)])
    path = tmp_path / "c.parquet"
    assert write_table(con, "c", path, HubCandidate, ["airport"]) == 2
    rows = con.execute(
        f"SELECT airport, weather_share, weather_share_by_season FROM '{path.as_posix()}'"
    ).fetchall()
    assert rows[0][0] == "DEN"  # sorted
    assert rows[0][1] == 0.123457  # rounded to 6 decimals
    assert rows[0][2] == {"winter": 0.2, "spring": None, "summer": 0.1, "autumn": 0.0}


def test_nested_lists_of_structs() -> None:
    con = duckdb.connect()
    slot = ScheduleSlot(
        slot_id="WN-CMH-ORD-1000",
        marketing_airline="WN",
        origin="CMH",
        dest="ORD",
        ref_dep_local_min=600,
        min_dep_local_min=600,
        max_dep_local_min=600,
        scheduled_days=10,
        recurrence=1.0,
        flight_numbers=[
            FlightNumberShare(flight_number="WN1001", share_of_days=0.5),
            FlightNumberShare(flight_number="WN2001", share_of_days=0.5),
        ],
    )
    models_to_table(con, "s", ScheduleSlot, [slot])
    assert con.execute("SELECT flight_numbers[2].flight_number FROM s").fetchall() == [("WN2001",)]


def test_identical_tables_give_identical_bytes_and_hashes(tmp_path: Path) -> None:
    con = duckdb.connect()
    models_to_table(con, "c", HubCandidate, [candidate("ORD", 1.0), candidate("DEN", 0.5)])
    a, b = tmp_path / "a.parquet", tmp_path / "b.parquet"
    write_table(con, "c", a, HubCandidate, ["airport"])
    models_to_table(con, "c", HubCandidate, [candidate("DEN", 0.5), candidate("ORD", 1.0)])
    write_table(con, "c", b, HubCandidate, ["airport"])
    assert a.read_bytes() == b.read_bytes()
    assert table_hash(con, a) == table_hash(con, b)


def test_aware_datetimes_stored_as_naive_utc() -> None:
    from flight_pipeline.storage import _plain  # pyright: ignore[reportPrivateUsage]

    aware = dt.datetime(2026, 1, 5, 8, 0, tzinfo=dt.timezone(dt.timedelta(hours=-5)))
    assert _plain(aware) == dt.datetime(2026, 1, 5, 13, 0)  # noqa: DTZ001
