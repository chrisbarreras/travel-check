"""End-to-end: every stage after acquire on a synthetic year (User Story 6, FR-033).

Expected results follow from the synthetic design (tests/integration/synthetic.py), not from
the pipeline: the hand-computed small fixture is covered by the unit tests.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from flight_pipeline.cli import main
from flight_pipeline.models import Finding


def itinerary_layovers(root: Path) -> dict[str, int]:
    path = (root / "derived" / "itineraries.parquet").as_posix()
    rows = (
        duckdb.connect()
        .execute(f"SELECT itinerary_id, median_layover_min FROM read_parquet('{path}')")
        .fetchall()
    )
    return {i: int(v) for i, v in rows}


def test_renumbering_airline_has_itineraries(finished: Path) -> None:
    # WN alternates flight numbers daily: only schedule-slot identity sees it (SC-001)
    path = (finished / "derived" / "itineraries.parquet").as_posix()
    n = (
        duckdb.connect()
        .execute(f"SELECT count(*) FROM read_parquet('{path}') WHERE airline_in = 'WN'")
        .fetchone()
    )
    assert n is not None
    assert n[0] > 0


def finding(root: Path) -> Finding:
    return Finding.model_validate_json((root / "reports" / "summary.json").read_text())


def test_all_outputs_written(finished: Path) -> None:
    for name in (
        "flights.parquet",
        "passengers.parquet",
        "sold_routings.parquet",
        "od_exclusions.parquet",
        "airports.parquet",
        "hub_candidates.parquet",
        "hub_selection.parquet",
        "itineraries.parquet",
        "od_selection.parquet",
        "sensitivity_scenarios.parquet",
        "daily_outcomes.parquet",
        "itinerary_results.parquet",
        "comparable_pairs.parquet",
        "showcase_routes.parquet",
        "showcase_comparisons.parquet",
        "curation.json",
    ):
        assert (finished / "derived" / name).exists(), name
    for name in ("summary.json", "summary.md", "manifest.json", "quality.json"):
        assert (finished / "reports" / name).exists(), name


def test_hub_selection_follows_design(finished: Path) -> None:
    f = finding(finished)
    hubs = {h.airport: h.reason for h in f.hubs}
    assert len(hubs) == 5
    assert "SEA" in hubs  # the only hub carrying AS
    assert f.unmet_constraints == []
    text = (finished / "reports" / "summary.md").read_text(encoding="utf-8")
    for hub in ("ORD", "MSP"):
        assert f"| {hub} |" in text
    assert "winter" in text
    assert "summer" in text


def test_pairs_and_results_follow_design(finished: Path) -> None:
    f = finding(finished)
    assert len(f.od_pairs) == 10
    assert all(p.regional_origin for p in f.od_pairs)
    layover = itinerary_layovers(finished)
    # the CMH second bank is scheduled at the 30-minute minimum (tight by design): compare
    # weather hubs on the first bank's 90-minute connections only
    rates = {r.itinerary_id: r for r in f.default_results if layover[r.itinerary_id] >= 60}
    assert all(r.status == "ok" for r in rates.values())
    reliable = [
        r.feasibility_rate
        for i, r in rates.items()
        if i.split("-")[1] in ("DFW", "SEA", "CLT", "DEN")
    ]
    stormy = [
        r.feasibility_rate
        for i, r in rates.items()
        if i.split("-")[1] in ("ORD", "MSP", "ATL", "PHX")
    ]
    assert reliable
    assert stormy
    assert min(x or 0 for x in reliable) > max(x or 0 for x in stormy)


def test_showcases_and_decision_follow_design(finished: Path) -> None:
    f = finding(finished)
    assert len(f.showcase_examples) >= 3
    for p in f.showcase_examples:
        assert p.rate_diff is not None
        assert p.rate_diff >= 0.10
        assert p.ci_low is not None
        assert p.ci_low > 0
        assert not p.assumption_sensitive
    assert f.criterion_min_examples_met
    assert f.criterion_min_hubs_met
    assert f.decision == "go"


def test_curation_follows_design(finished: Path) -> None:
    # caps hold on the synthetic showcase; the landing example is cross-hub (research R4)
    con = duckdb.connect()
    routes = (finished / "derived" / "showcase_routes.parquet").as_posix()
    comps = (finished / "derived" / "showcase_comparisons.parquet").as_posix()
    rows = con.execute(
        f"SELECT route_id, rank, share_of_showcase FROM read_parquet('{routes}') ORDER BY rank"
    ).fetchall()
    assert rows
    assert [r[1] for r in rows] == list(range(1, len(rows) + 1))
    meta = json.loads((finished / "derived" / "curation.json").read_text())
    if not any(s.startswith("route ") for s in meta["shortfalls"]):
        assert max(r[2] for r in rows) <= 0.333 + 1e-9
    landing = con.execute(
        f"SELECT comparison_id, cross_hub FROM read_parquet('{comps}') WHERE landing"
    ).fetchall()
    assert len(landing) == 1
    assert landing[0][0] == meta["landing_comparison_id"]
    assert landing[0][1] is True


def test_manifest_records_sources_packages_and_hashes(finished: Path) -> None:
    manifest = json.loads((finished / "reports" / "manifest.json").read_text())
    assert len(manifest["config_sha256"]) == 64
    assert len(manifest["sources"]) == 17  # 12 on-time months + 4 DB1B quarters + T-100
    assert manifest["packages"]["duckdb"]
    assert "flights.parquet" in manifest["outputs"]
    assert "summary.json" in manifest["outputs"]
    assert set(manifest["run"]) >= {"run_at", "runtime_min", "runtime_exceeded", "machine"}


def test_run_command_records_runtime(
    run_root: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    root, config = run_root
    assert main(["run", "--no-acquire", "--config", str(config)]) == 0
    out, _ = capsys.readouterr()
    assert "runtime" in out
    run = json.loads((root / "reports" / "manifest.json").read_text())["run"]
    assert run["runtime_min"] is not None
    assert run["runtime_exceeded"] is False


def test_report_files_use_lf_line_endings(finished: Path) -> None:
    for name in ("summary.json", "summary.md", "manifest.json", "quality.json"):
        assert bytes([13]) not in (finished / "reports" / name).read_bytes(), name


def test_sold_routing_rules_follow_design(finished: Path) -> None:
    f = finding(finished)
    assert f.db1b_quarters == ["2024-3", "2024-4", "2025-1", "2025-2"]
    assert 0 < f.db1b_unknown_airline_share < 0.01
    assert {(e.origin, e.dest) for e in f.od_exclusions} == {(p.origin, p.dest) for p in f.od_pairs}
    for e in f.od_exclusions:
        assert e.excluded_recurrence == 0  # every first-bank connection works every day
        assert e.excluded_bounds > 0  # the later banks can never connect within the limit
        assert e.qualifying > 0
    # UA through DEN to BOS is sold below the minimum: never an itinerary
    assert not any(
        ":UA" in r.itinerary_id and "-DEN-BOS:" in r.itinerary_id for r in f.default_results
    )
    layover = itinerary_layovers(finished)
    for p in f.showcase_examples:
        tight = min(layover[p.itinerary_a], layover[p.itinerary_b]) < 45
        # tight second-bank connections cannot be compared at a 45-minute minimum
        assert p.settings_compared == (6 if tight else 9)
    text = (finished / "reports" / "summary.md").read_text(encoding="utf-8")
    assert "## Itinerary rules applied" in text
    assert "DB1B quarters 2024-3 to 2025-2" in text
    assert "Sold passengers on routing A / B" in text
