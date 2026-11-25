"""Deterministic Parquet output and model tables (research R8)."""

import datetime as dt
from pathlib import Path

import duckdb

from flight_pipeline.models import HubCandidate, Itinerary, PatternKey, SeasonShares
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


def test_nested_pattern_keys() -> None:
    con = duckdb.connect()
    leg_in = PatternKey(marketing_airline="AA", flight_number=1, origin="CMH", dest="ORD")
    leg_out = PatternKey(marketing_airline="AA", flight_number=2, origin="ORD", dest="SAN")
    it = Itinerary(
        itinerary_id="CMH-ORD-SAN:AA1+AA2",
        origin="CMH",
        hub="ORD",
        dest="SAN",
        inbound=leg_in,
        outbound=leg_out,
        partner_connection=False,
        median_layover_min=60,
        median_travel_min=300,
        median_dep_local_min=480,
        connect_share=0.9,
        sold_passengers=40,
    )
    models_to_table(con, "i", Itinerary, [it])
    assert con.execute("SELECT inbound.flight_number, outbound.dest FROM i").fetchall() == [
        (1, "SAN")
    ]


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
