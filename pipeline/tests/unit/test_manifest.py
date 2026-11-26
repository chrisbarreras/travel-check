"""The run block of the manifest keeps the measured runtime (SC-008), and the showcase
manifest extends the carry-over rule to the code version (specs/002 FR-027)."""

from typing import Any

from flight_pipeline.showcase.models import ShowcaseManifest
from flight_pipeline.stages import merge_run, showcase_manifest


def run_block(runtime: float | None, at: str) -> dict[str, object]:
    return {
        "run_at": at,
        "runtime_min": runtime,
        "runtime_limit_min": 30.0,
        "runtime_exceeded": None if runtime is None else runtime > 30.0,
        "machine": {"cpu_count": 16, "ram_gb": 15.4},
    }


def test_full_run_records_its_runtime() -> None:
    new = run_block(7.1, "2026-11-25T05:06:14+00:00")
    assert merge_run(run_block(6.0, "earlier"), new, same_inputs=True) == {
        **new,
        "runtime_measured_at": new["run_at"],
    }


def test_report_alone_keeps_the_last_measured_runtime() -> None:
    previous = run_block(7.1, "2026-11-25T05:06:14+00:00")
    merged = merge_run(previous, run_block(None, "2026-11-25T05:33:00+00:00"), same_inputs=True)
    assert merged["runtime_min"] == 7.1
    assert merged["runtime_exceeded"] is False
    assert merged["runtime_measured_at"] == "2026-11-25T05:06:14+00:00"
    assert merged["run_at"] == "2026-11-25T05:33:00+00:00"


def test_report_alone_without_earlier_runtime_says_not_measured() -> None:
    merged = merge_run(None, run_block(None, "now"), same_inputs=False)
    assert merged["runtime_min"] is None
    assert merged["runtime_measured_at"] is None


def test_runtime_not_carried_over_when_config_or_sources_changed() -> None:
    previous = run_block(7.1, "2026-11-25T05:06:14+00:00")
    merged = merge_run(previous, run_block(None, "later"), same_inputs=False)
    assert merged["runtime_min"] is None
    assert merged["runtime_exceeded"] is None
    assert merged["runtime_measured_at"] is None


# --- Showcase manifest (specs/002) ---

IDENTITY: dict[str, Any] = {
    "sources": [{"name": "ontime/2024-07", "sha256": "a" * 64, "pinned": True}],
    "config_sha256": "c" * 64,
    "notes_sha256": "n" * 64,
    "code_version": "0.2.0",
    "git_commit": "abc123",
    "packages": {"duckdb": "1.4.0", "python": "3.13"},
}


def showcase_run(runtime: float | None, at: str = "2026-11-26T10:00:00+00:00") -> dict[str, Any]:
    return {
        "run_at": at,
        "runtime_min": runtime,
        "runtime_limit_min": 30,
        "runtime_exceeded": None if runtime is None else runtime > 30,
        "machine": {"cpu_count": 8, "ram_gb": 16.0},
    }


def test_records_every_identity_and_output_checksum() -> None:
    m = showcase_manifest(
        None, identity=IDENTITY, outputs={"index.json": "f" * 64}, run=showcase_run(12.5)
    )
    ShowcaseManifest.model_validate(m)
    for key in IDENTITY:
        assert m[key] == IDENTITY[key]
    assert m["outputs"] == {"index.json": "f" * 64}
    assert m["run"]["runtime_min"] == 12.5
    assert m["run"]["runtime_measured_at"] == "2026-11-26T10:00:00+00:00"


def test_runtime_carried_over_only_when_every_identity_matches() -> None:
    first = showcase_manifest(None, identity=IDENTITY, outputs={}, run=showcase_run(12.5))
    later = showcase_run(None, at="2026-11-27T09:00:00+00:00")
    same = showcase_manifest(first, identity=IDENTITY, outputs={}, run=later)
    assert same["run"]["runtime_min"] == 12.5
    assert same["run"]["runtime_measured_at"] == "2026-11-26T10:00:00+00:00"
    for key, value in (
        ("config_sha256", "d" * 64),
        ("notes_sha256", "m" * 64),
        ("code_version", "0.3.0"),
        ("git_commit", "def456"),
        ("packages", {"duckdb": "1.5.0", "python": "3.13"}),
        ("sources", []),
    ):
        changed = showcase_manifest(first, identity={**IDENTITY, key: value}, outputs={}, run=later)
        assert changed["run"]["runtime_min"] is None, key
        assert changed["run"]["runtime_measured_at"] is None, key


def test_a_measured_runtime_replaces_the_old_one() -> None:
    first = showcase_manifest(None, identity=IDENTITY, outputs={}, run=showcase_run(12.5))
    again = showcase_manifest(
        first, identity=IDENTITY, outputs={}, run=showcase_run(14.0, "2026-11-28T00:00:00+00:00")
    )
    assert again["run"]["runtime_min"] == 14.0
    assert again["run"]["runtime_measured_at"] == "2026-11-28T00:00:00+00:00"
