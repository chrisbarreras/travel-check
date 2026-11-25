"""The run block of the manifest keeps the measured runtime (SC-008)."""

from flight_pipeline.stages import merge_run


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
