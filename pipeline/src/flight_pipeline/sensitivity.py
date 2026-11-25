"""Sensitivity scenarios (FR-027) and assumption-sensitivity flags (FR-028).

Each scenario is one combination of minimum connection time, boarding cutoff and recurrence
threshold. Hub and origin/destination pair selection stay fixed at the defaults; itineraries
for the selected pairs are rebuilt per scenario with the same rules (research R12), because
the minimum connection time moves the layover window and the recurrence threshold applies to
the share of days the two flights connect. The scenario moves every minimum
connection time (default, partner, per-hub) by its difference from the default, for example
partner connections use 35, 45 and 60 minutes when the default is 20, 30 and 45; the minimum
is also the transfer time in the feasibility threshold.
"""

from __future__ import annotations

import datetime as dt
import itertools
from collections.abc import Mapping, Sequence

import duckdb

from flight_pipeline.config import Itineraries, Sensitivity
from flight_pipeline.feasibility import classify, daily_slack, itinerary_results
from flight_pipeline.itineraries import build_itineraries
from flight_pipeline.models import SensitivityScenario
from flight_pipeline.od_selection import pairs_without_itineraries


def scenario_id(mct: int, cutoff: int, recurrence: float) -> str:
    return f"mct{mct}_cut{cutoff}_rec{round(recurrence * 100)}"


def scenarios(sens: Sensitivity, defaults: tuple[int, int, float]) -> list[SensitivityScenario]:
    out = [
        SensitivityScenario(
            scenario_id=scenario_id(m, c, r),
            min_connection_min=m,
            boarding_cutoff_min=c,
            recurrence_threshold=r,
            is_default=(m, c, r) == defaults,
        )
        for m, c, r in itertools.product(
            sorted(sens.min_connection_min),
            sorted(sens.boarding_cutoff_min),
            sorted(sens.recurrence_threshold),
        )
    ]
    return sorted(out, key=lambda s: s.scenario_id)


def scenario_rules(rules: Itineraries, mct: int, default_mct: int | None = None) -> Itineraries:
    """Rules for a scenario minimum connection time ``mct``. Every minimum (default, partner
    and per-hub) moves by the scenario's difference from the default, so partner and per-hub
    connections are stress-tested by the same amount."""
    base = rules.min_connection_default_min if default_mct is None else default_mct
    delta = mct - base
    return rules.model_copy(
        update={
            "min_connection_default_min": mct,
            "min_connection_partner_min": max(0, rules.min_connection_partner_min + delta),
            "min_connection_by_hub": {
                h: max(0, v + delta) for h, v in rules.min_connection_by_hub.items()
            },
        }
    )


def evaluate_scenarios(
    con: duckdb.DuckDBPyConnection,
    flights: str,
    patterns: str,
    hubs: Sequence[str],
    pairs: Sequence[tuple[str, str]],
    rules: Itineraries,
    sens: Sensitivity,
    defaults: tuple[int, int, float],
    min_sample_days: int,
    period: tuple[dt.date, dt.date],
    target: str,
    default_classified: str,
    *,
    sold: str,
) -> list[str]:
    """Create ``target`` with ItineraryResult rows for every scenario and
    ``default_classified`` with the default scenario's daily rows; also
    ``{target}_itineraries`` (scenario_id, itinerary_id, hub). Returns selected pairs that
    have no qualifying itinerary in some scenario, as ``"ORIGIN-DEST (scenario_id)"``."""
    con.execute("CREATE OR REPLACE TEMP TABLE _sel_pairs (origin VARCHAR, dest VARCHAR)")
    if pairs:
        con.executemany("INSERT INTO _sel_pairs VALUES (?, ?)", list(pairs))
    all_scenarios = scenarios(sens, defaults)
    result_tables: list[str] = []
    itinerary_tables: list[str] = []
    missing: list[str] = []
    for mct, rec in itertools.product(
        sorted(sens.min_connection_min), sorted(sens.recurrence_threshold)
    ):
        r = scenario_rules(rules, mct, rules.min_connection_default_min)
        build_itineraries(
            con,
            patterns,
            hubs,
            r,
            "_sc_it",
            rec,
            flights=flights,
            sold=sold,
            period=period,
            od_pairs=list(pairs),
        )
        available = {
            (o, d) for o, d in con.execute("SELECT DISTINCT origin, dest FROM _sc_it").fetchall()
        }
        daily_slack(con, flights, "_sc_it", r, period, "_sc_slack")
        for cutoff in sorted(sens.boarding_cutoff_min):
            sid = scenario_id(mct, cutoff, rec)
            missing += [f"{p} ({sid})" for p in pairs_without_itineraries(pairs, available)]
            classify(con, "_sc_slack", cutoff, "_sc_classified")
            if (mct, cutoff, rec) == defaults:
                con.execute(
                    f"CREATE OR REPLACE TABLE {default_classified} AS SELECT * FROM _sc_classified"
                )
            table = f"_res_{len(result_tables)}"
            itinerary_results(con, "_sc_classified", sid, min_sample_days, period, table, "_sc_it")
            result_tables.append(table)
            it_table = f"_its_{len(itinerary_tables)}"
            con.execute(
                f"CREATE OR REPLACE TEMP TABLE {it_table} AS "
                f"SELECT '{sid}' AS scenario_id, itinerary_id, hub FROM _sc_it"
            )
            itinerary_tables.append(it_table)
    assert len(result_tables) == len(all_scenarios)
    con.execute(
        f"CREATE OR REPLACE TABLE {target} AS "
        + " UNION ALL ".join(f"SELECT * FROM {t}" for t in result_tables)
        + " ORDER BY scenario_id, itinerary_id"
    )
    con.execute(
        f"CREATE OR REPLACE TABLE {target}_itineraries AS "
        + " UNION ALL ".join(f"SELECT * FROM {t}" for t in itinerary_tables)
    )
    for t in result_tables + itinerary_tables:
        con.execute(f"DROP TABLE {t}")
    return sorted(missing)


def reversal_flags(
    pairs: Sequence[tuple[str, str]],
    rates: Mapping[str, Mapping[str, float | None]],
    default: str,
    scenario_ids: Sequence[str] | None = None,
) -> tuple[dict[tuple[str, str], bool], list[tuple[str, str, str]]]:
    """FR-028. ``rates[scenario][itinerary]`` is the feasibility rate (None = insufficient
    data; absent = itinerary does not qualify in that scenario). A pair is
    assumption-sensitive when its default order is strict and some scenario strictly
    reverses it. Scenarios where either itinerary is absent or has insufficient data are
    returned as (a, b, scenario) and never count as a reversal."""
    flags: dict[tuple[str, str], bool] = {}
    missing: list[tuple[str, str, str]] = []
    base = rates.get(default, {})
    all_ids = sorted(set(scenario_ids) if scenario_ids is not None else set(rates))
    for a, b in pairs:
        ra, rb = base.get(a), base.get(b)
        sign = 0 if ra is None or rb is None else (ra > rb) - (ra < rb)
        sensitive = False
        for sid in all_ids:
            if sid == default:
                continue
            sa, sb = rates.get(sid, {}).get(a), rates.get(sid, {}).get(b)
            if sa is None or sb is None:
                missing.append((a, b, sid))
                continue
            s = (sa > sb) - (sa < sb)
            if sign != 0 and s == -sign:
                sensitive = True
        flags[(a, b)] = sensitive
    return flags, missing


def settings_compared(
    pairs: Sequence[tuple[str, str]],
    rates: Mapping[str, Mapping[str, float | None]],
    scenario_rows: Sequence[SensitivityScenario],
) -> dict[tuple[str, str], int]:
    """Distinct (minimum connection time, boarding cutoff) settings, the default included, at
    which both itineraries of a pair had a rate (sufficient data) in some recurrence
    scenario. Rates depend only on these two settings; the recurrence threshold only changes
    which itineraries qualify (research R12)."""
    return {k: len(v) for k, v in _compared(pairs, rates, scenario_rows).items()}


def missing_settings(
    pairs: Sequence[tuple[str, str]],
    rates: Mapping[str, Mapping[str, float | None]],
    scenario_rows: Sequence[SensitivityScenario],
) -> dict[tuple[str, str], list[tuple[int, int]]]:
    """The (minimum connection time, boarding cutoff) settings at which a pair was not
    compared, sorted; the complement of ``settings_compared``."""
    every = {(s.min_connection_min, s.boarding_cutoff_min) for s in scenario_rows}
    return {k: sorted(every - v) for k, v in _compared(pairs, rates, scenario_rows).items()}


def _compared(
    pairs: Sequence[tuple[str, str]],
    rates: Mapping[str, Mapping[str, float | None]],
    scenario_rows: Sequence[SensitivityScenario],
) -> dict[tuple[str, str], set[tuple[int, int]]]:
    out: dict[tuple[str, str], set[tuple[int, int]]] = {}
    for a, b in pairs:
        settings: set[tuple[int, int]] = set()
        for s in scenario_rows:
            sr = rates.get(s.scenario_id, {})
            if sr.get(a) is not None and sr.get(b) is not None:
                settings.add((s.min_connection_min, s.boarding_cutoff_min))
        out[(a, b)] = settings
    return out


def reversals_by_scenario(
    pairs: Sequence[tuple[str, str]],
    rates: Mapping[str, Mapping[str, float | None]],
    default: str,
) -> dict[str, int]:
    """Number of pairs whose strict default order is strictly reversed, per scenario."""
    base = rates[default]
    out: dict[str, int] = {}
    for sid in sorted(rates):
        if sid == default:
            continue
        n = 0
        for a, b in pairs:
            ra, rb, sa, sb = base.get(a), base.get(b), rates[sid].get(a), rates[sid].get(b)
            if ra is None or rb is None or sa is None or sb is None:
                continue
            if (ra - rb) * (sa - sb) < 0:
                n += 1
        out[sid] = n
    return out
