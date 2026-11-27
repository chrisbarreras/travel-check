"""Validation rules from data-model.md."""

import datetime as dt
from typing import Any

import pytest
from pydantic import ValidationError

from flight_pipeline.models import (
    DailyOutcome,
    FlightRecord,
    ItineraryResult,
    SensitivityScenario,
    validate_scenarios,
)

UTC = dt.UTC


def flight(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "marketing_airline": "AA",
        "operating_airline": "MQ",
        "flight_number": 3100,
        "service_date": dt.date(2026, 1, 5),
        "origin": "CMH",
        "dest": "ORD",
        "sched_dep_utc": dt.datetime(2026, 1, 5, 13, 0, tzinfo=UTC),
        "sched_arr_utc": dt.datetime(2026, 1, 5, 14, 20, tzinfo=UTC),
        "sched_dep_local_min": 480,
        "sched_arr_local_min": 500,
        "sched_elapsed_min": 80,
        "actual_dep_utc": dt.datetime(2026, 1, 5, 13, 5, tzinfo=UTC),
        "actual_arr_utc": dt.datetime(2026, 1, 5, 14, 22, tzinfo=UTC),
        "cancelled": False,
        "diverted": False,
        "cancellation_code": None,
        "weather_delay_min": None,
        "weather_affected": False,
        "quality_flag": "ok",
    }
    base.update(overrides)
    return base


def test_valid_flight() -> None:
    FlightRecord.model_validate(flight())


def test_flight_arrival_must_follow_departure() -> None:
    with pytest.raises(ValidationError, match="sched_arr_utc"):
        FlightRecord.model_validate(flight(sched_arr_utc=dt.datetime(2026, 1, 5, 12, tzinfo=UTC)))


def test_ok_operated_flight_needs_actual_times() -> None:
    with pytest.raises(ValidationError, match="actual"):
        FlightRecord.model_validate(flight(actual_arr_utc=None))


@pytest.mark.parametrize(
    "overrides",
    [
        {
            "cancelled": True,
            "cancellation_code": "B",
            "actual_dep_utc": None,
            "actual_arr_utc": None,
        },
        {"diverted": True, "actual_arr_utc": None},
        {"quality_flag": "missing_actual_times", "actual_dep_utc": None, "actual_arr_utc": None},
    ],
)
def test_actual_times_may_be_missing_when_not_ok_or_not_operated(overrides: dict[str, Any]) -> None:
    FlightRecord.model_validate(flight(**overrides))


def test_flight_times_must_be_utc_aware() -> None:
    with pytest.raises(ValidationError):
        FlightRecord.model_validate(flight(sched_dep_utc=dt.datetime(2026, 1, 5, 13, 0)))  # noqa: DTZ001
    with pytest.raises(ValidationError, match="UTC"):
        FlightRecord.model_validate(
            flight(
                sched_dep_utc=dt.datetime(
                    2026, 1, 5, 8, 0, tzinfo=dt.timezone(dt.timedelta(hours=-5))
                )
            )
        )


def test_cancellation_code_values() -> None:
    with pytest.raises(ValidationError):
        FlightRecord.model_validate(flight(cancelled=True, cancellation_code="E"))


def test_quality_flag_values() -> None:
    with pytest.raises(ValidationError):
        FlightRecord.model_validate(flight(quality_flag="weird"))


def result(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "itinerary_id": "CMH-ORD-SAN:AA3100+AA1500",
        "scenario_id": "mct30_cut15_rec60",
        "paired_days": 40,
        "excluded_not_connecting": 2,
        "excluded_quality": 1,
        "excluded_end_of_period": 0,
        "feasibility_rate": 0.75,
        "status": "ok",
        "count_feasible": 30,
        "count_insufficient_time": 6,
        "count_cancelled": 3,
        "count_diverted": 1,
        "slack_min": -12,
        "slack_p10": 20,
        "slack_p50": 55,
        "slack_p90": 90,
        "period_start": dt.date(2025, 10, 1),
        "period_end": dt.date(2026, 9, 30),
    }
    base.update(overrides)
    return base


def test_valid_result() -> None:
    ItineraryResult.model_validate(result())


def test_rate_null_exactly_when_insufficient() -> None:
    with pytest.raises(ValidationError, match="feasibility_rate"):
        ItineraryResult.model_validate(result(status="insufficient_data"))
    with pytest.raises(ValidationError, match="feasibility_rate"):
        ItineraryResult.model_validate(result(feasibility_rate=None))
    ItineraryResult.model_validate(result(status="insufficient_data", feasibility_rate=None))


def test_result_counts_sum_to_paired_days() -> None:
    with pytest.raises(ValidationError, match="paired_days"):
        ItineraryResult.model_validate(result(count_feasible=29))


def test_excluded_counts_non_negative() -> None:
    with pytest.raises(ValidationError):
        ItineraryResult.model_validate(result(excluded_quality=-1))


def scenario(sid: str, *, default: bool) -> SensitivityScenario:
    return SensitivityScenario(
        scenario_id=sid,
        min_connection_min=30,
        boarding_cutoff_min=15,
        recurrence_threshold=0.6,
        is_default=default,
    )


def test_exactly_one_default_scenario() -> None:
    validate_scenarios([scenario("a", default=True), scenario("b", default=False)])
    with pytest.raises(ValueError, match="exactly one"):
        validate_scenarios([scenario("a", default=True), scenario("b", default=True)])
    with pytest.raises(ValueError, match="exactly one"):
        validate_scenarios([scenario("a", default=False)])


def test_daily_outcome_values() -> None:
    DailyOutcome(
        itinerary_id="x", service_date=dt.date(2026, 1, 1), raw_slack_min=40, outcome="feasible"
    )
    with pytest.raises(ValidationError):
        DailyOutcome(
            itinerary_id="x",
            service_date=dt.date(2026, 1, 1),
            raw_slack_min=40,
            outcome="late",  # pyright: ignore[reportArgumentType]
        )


def test_validate_table_reads_naive_timestamps_as_utc_and_checks_columns() -> None:
    import duckdb

    from flight_pipeline.models import PassengerTraffic, validate_table

    con = duckdb.connect()
    con.execute(
        "CREATE TABLE t AS SELECT * FROM (VALUES (2026, 1, 'ORD', 'AA', 10)) "
        "v(year, month, origin, carrier, passengers)"
    )
    assert validate_table(con, "t", PassengerTraffic) == 1
    con.execute("CREATE TABLE bad AS SELECT year, month, origin, carrier FROM t")
    with pytest.raises(ValueError, match=r"missing \['passengers'\]"):
        validate_table(con, "bad", PassengerTraffic)
    con.execute("CREATE TABLE neg AS SELECT year, month, origin, carrier, -1 AS passengers FROM t")
    with pytest.raises(ValidationError):
        validate_table(con, "neg", PassengerTraffic)

    rec = flight()
    rec["sched_dep_utc"] = rec["sched_dep_utc"].replace(tzinfo=None)
    rec["sched_arr_utc"] = rec["sched_arr_utc"].replace(tzinfo=None)
    rec["actual_dep_utc"] = rec["actual_dep_utc"].replace(tzinfo=None)
    rec["actual_arr_utc"] = rec["actual_arr_utc"].replace(tzinfo=None)
    cols = list(rec)
    con.execute(f"CREATE TABLE f ({', '.join(c + ' ' + _sqltype(rec[c]) for c in cols)})")
    con.execute(f"INSERT INTO f VALUES ({', '.join('?' for _ in cols)})", [rec[c] for c in cols])
    assert validate_table(con, "f", FlightRecord) == 1


def _sqltype(v: Any) -> str:
    if isinstance(v, bool):
        return "BOOLEAN"
    if isinstance(v, int):
        return "INTEGER"
    if isinstance(v, dt.datetime):
        return "TIMESTAMP"
    if isinstance(v, dt.date):
        return "DATE"
    return "VARCHAR"
