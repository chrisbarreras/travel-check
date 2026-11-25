"""Sensitivity scenarios and assumption-sensitivity flags (User Story 4; FR-027, FR-028)."""

import datetime as dt
from pathlib import Path

import duckdb
import pytest

from flight_pipeline.config import Sensitivity, load_config
from flight_pipeline.sensitivity import (
    evaluate_scenarios,
    reversal_flags,
    scenario_id,
    scenarios,
    settings_compared,
)
from tests.unit.test_itineraries import PERIOD, rules

REPO = Path(__file__).resolve().parents[3]


def test_27_scenarios_with_deterministic_ids_and_one_default() -> None:
    cfg = load_config(REPO / "config" / "phase1.toml")
    sc = scenarios(cfg.sensitivity, (30, 15, 0.60))
    assert len(sc) == 27
    assert len({s.scenario_id for s in sc}) == 27
    assert [s.scenario_id for s in sc if s.is_default] == ["mct30_cut15_rec60"]
    assert sc[0].scenario_id == "mct20_cut10_rec50"
    assert sc == scenarios(cfg.sensitivity, (30, 15, 0.60))
    assert scenario_id(45, 20, 0.75) == "mct45_cut20_rec75"


def run_scenarios(con: duckdb.DuckDBPyConnection, pairs: list[tuple[str, str]]) -> list[str]:
    sens = Sensitivity(
        min_connection_min=[20, 30, 45],
        boarding_cutoff_min=[10, 15, 20],
        recurrence_threshold=[0.50, 0.60, 0.75],
    )
    return evaluate_scenarios(
        con,
        "flights",
        "patterns",
        ["ORD"],
        pairs,
        rules(min_sold_passengers=10),  # CMH:ORD:DEN AA:AA has 12
        sens,
        (30, 15, 0.60),
        5,
        PERIOD,
        "results_all",
        "classified_default",
        sold="sold",
    )


def ids_for(con: duckdb.DuckDBPyConnection, scenario: str) -> list[str]:
    return [
        r[0]
        for r in con.execute(
            "SELECT itinerary_id FROM results_all WHERE scenario_id = ? ORDER BY 1", [scenario]
        ).fetchall()
    ]


def test_itineraries_rebuilt_per_recurrence_for_selected_pairs_only(
    con: duckdb.DuckDBPyConnection,
) -> None:
    run_scenarios(con, [("CMH", "DEN"), ("CMH", "SAN")])
    assert ids_for(con, "mct30_cut15_rec60") == [
        "CMH-ORD-DEN:AA3100+AA1510",
        "CMH-ORD-DEN:UA7000+UA7003",
        "CMH-ORD-DEN:UA7002+UA7003",
        "CMH-ORD-SAN:AA3100+AA1500",
        "CMH-ORD-SAN:AA3100+AA1506",
    ]
    assert "CMH-ORD-DEN:AA3100+AA1508" in ids_for(con, "mct30_cut15_rec50")
    assert "CMH-ORD-DEN:AA3100+AA1510" not in ids_for(con, "mct30_cut15_rec75")
    # no itinerary outside the selected pairs is evaluated (hub and pair selection fixed)
    all_ids = {r[0] for r in con.execute("SELECT itinerary_id FROM results_all").fetchall()}
    assert not any(i.startswith(("CMH-ORD-SEA", "CMH-ORD-PHX")) for i in all_ids)


def test_results_for_every_scenario(con: duckdb.DuckDBPyConnection) -> None:
    run_scenarios(con, [("CMH", "SAN")])
    n = con.execute("SELECT count(DISTINCT scenario_id) FROM results_all").fetchone()
    assert n == (27,)


def test_minimum_connection_scenario_changes_rule_and_threshold(
    con: duckdb.DuckDBPyConnection,
) -> None:
    run_scenarios(con, [("CMH", "SAN")])
    rate = {
        s: con.execute(
            "SELECT count_feasible FROM results_all WHERE scenario_id = ? "
            "AND itinerary_id = 'CMH-ORD-SAN:AA3100+AA1500'",
            [s],
        ).fetchone()
        for s in ("mct20_cut15_rec60", "mct30_cut15_rec60", "mct45_cut15_rec60")
    }
    # slack values 95, 40, 45, -28, 90: feasible counts at thresholds 35, 45 and 60
    assert rate == {"mct20_cut15_rec60": (4,), "mct30_cut15_rec60": (3,), "mct45_cut15_rec60": (2,)}


def test_default_daily_outcomes_kept(con: duckdb.DuckDBPyConnection) -> None:
    run_scenarios(con, [("CMH", "SAN")])
    n = con.execute(
        "SELECT count(*) FROM classified_default WHERE status = 'paired' "
        "AND itinerary_id = 'CMH-ORD-SAN:AA3100+AA1500'"
    ).fetchone()
    assert n == (8,)


def test_pairs_without_itineraries_in_a_scenario_reported(
    con: duckdb.DuckDBPyConnection,
) -> None:
    missing = run_scenarios(con, [("CMH", "DEN"), ("CMH", "SAN")])
    # At 45 min, UA7002 + UA7003 connects on 2 of 10 days and UA7000 + UA7003 (40 min) not at
    # all, so CMH-DEN has only AA1510 (60%); at 75% it has no itinerary.
    assert "CMH-DEN (mct45_cut15_rec75)" in missing
    assert "CMH-DEN (mct30_cut15_rec75)" not in missing  # UA7002 + UA7003 connects daily
    assert not any(m.startswith("CMH-SAN") for m in missing)


# --- Reversal flags ----------------------------------------------------------------------

RATES = {
    "default": {"a": 0.80, "b": 0.60, "c": 0.70, "d": None, "e": 0.8, "f": 0.6},
    "s1": {"a": 0.75, "b": 0.70, "c": 0.72},  # a > b holds; c > b
    "s2": {"a": 0.55, "b": 0.65},  # a < b: reversal of (a, b); c missing
    "s3": {"a": 0.70, "b": 0.70, "c": None, "e": 0.7, "f": 0.7},  # ties are not reversals
}


@pytest.mark.parametrize(
    ("pair", "sensitive"),
    [
        (("a", "b"), True),
        (("b", "c"), False),
        (("a", "c"), False),
        (("a", "d"), False),
        (("e", "f"), False),  # only a tie (s3) against the default order: decisive for ties
    ],
)
def test_reversal_in_any_scenario_flags_pair(pair: tuple[str, str], sensitive: bool) -> None:
    flags, _ = reversal_flags(
        [("a", "b"), ("b", "c"), ("a", "c"), ("a", "d"), ("e", "f")], RATES, "default"
    )
    assert flags[pair] is sensitive


def test_missing_or_insufficient_in_scenario_is_reported_not_reversal() -> None:
    flags, missing = reversal_flags([("b", "c"), ("a", "c")], RATES, "default")
    assert flags[("a", "c")] is False
    assert ("a", "c", "s2") in missing
    assert ("a", "c", "s3") in missing
    assert ("b", "c", "s2") in missing


def test_dates_are_inclusive() -> None:
    assert (dt.date(2026, 1, 5), dt.date(2026, 1, 14)) == PERIOD


def test_reversals_counted_per_scenario() -> None:
    from flight_pipeline.sensitivity import reversals_by_scenario

    counts = reversals_by_scenario([("a", "b"), ("b", "c"), ("a", "c")], RATES, "default")
    assert counts == {"s1": 0, "s2": 1, "s3": 0}


def test_scenario_shifts_every_minimum_connection_time() -> None:
    from flight_pipeline.sensitivity import scenario_rules

    base = rules(min_connection_by_hub={"ORD": 40})
    for mct, same, partner, hub in ((20, 20, 35, 30), (30, 30, 45, 40), (45, 45, 60, 55)):
        r = scenario_rules(base, mct, default_mct=30)
        assert r.min_connection_for("DEN", partner=False) == same
        assert r.min_connection_for("DEN", partner=True) == partner
        assert r.min_connection_for("ORD", partner=False) == hub


def test_partner_itinerary_threshold_changes_across_scenarios(
    con: duckdb.DuckDBPyConnection,
) -> None:
    run_scenarios(con, [("CMH", "SEA")])
    feasible = {
        sid: con.execute(
            "SELECT count_feasible FROM results_all WHERE scenario_id = ? "
            "AND itinerary_id = 'CMH-ORD-SEA:AA3100+AS700'",
            [sid],
        ).fetchone()
        for sid in ("mct20_cut15_rec60", "mct30_cut15_rec60", "mct45_cut15_rec60")
    }
    # slack 70 on three days; partner thresholds 35+15, 45+15 and 60+15 minutes
    assert feasible == {
        "mct20_cut15_rec60": (3,),
        "mct30_cut15_rec60": (3,),
        "mct45_cut15_rec60": (0,),
    }


def test_scenario_without_any_results_counts_as_not_compared() -> None:
    rates = {"default": {"a": 0.8, "b": 0.6}, "s1": {"a": 0.7, "b": 0.6}}
    _, missing = reversal_flags([("a", "b")], rates, "default", ["default", "s1", "s2"])
    assert missing == [("a", "b", "s2")]


def test_recurrence_scenarios_apply_to_connection_share(
    con: duckdb.DuckDBPyConnection,
) -> None:
    run_scenarios(con, [("CMH", "DEN")])
    # UA7000 + UA7001 connect on 5 of 10 days: qualifies at 50% only
    assert "CMH-ORD-DEN:UA7000+UA7001" in ids_for(con, "mct30_cut15_rec50")
    assert "CMH-ORD-DEN:UA7000+UA7001" not in ids_for(con, "mct30_cut15_rec60")


def test_settings_compared_counts_distinct_connection_and_cutoff_settings() -> None:
    from flight_pipeline.models import SensitivityScenario

    def sc(m: int, c: int, r: float) -> SensitivityScenario:
        return SensitivityScenario(
            scenario_id=scenario_id(m, c, r),
            min_connection_min=m,
            boarding_cutoff_min=c,
            recurrence_threshold=r,
            is_default=(m, c, r) == (30, 15, 0.6),
        )

    rows = [sc(m, c, r) for m in (20, 30) for c in (10, 15) for r in (0.5, 0.6)]
    rates: dict[str, dict[str, float | None]] = {
        "mct30_cut15_rec60": {"a": 0.8, "b": 0.6},
        "mct30_cut15_rec50": {"a": 0.8, "b": 0.6},  # same setting as the default
        "mct20_cut15_rec50": {"a": 0.9, "b": 0.7},
        "mct20_cut10_rec60": {"a": 0.9, "b": None},  # insufficient data: not compared
        "mct30_cut10_rec50": {"a": 0.9},  # b does not qualify
    }
    assert settings_compared([("a", "b")], rates, rows) == {("a", "b"): 2}
