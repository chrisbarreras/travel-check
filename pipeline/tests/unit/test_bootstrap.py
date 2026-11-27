"""Paired day-level bootstrap for the difference in feasibility rates (research R5, FR-029)."""

import datetime as dt
import math
from typing import Any

import numpy as np
import pytest

from flight_pipeline.compare import paired_bootstrap as _paired_bootstrap


def paired_bootstrap(*args: Any, **kwargs: Any) -> tuple[float, float]:
    low, high = _paired_bootstrap(*args, **kwargs)
    assert low is not None
    assert high is not None
    return low, high


DAYS = [dt.date(2025, 10, 1) + dt.timedelta(days=i) for i in range(365)]


def outcomes(values: np.ndarray, days: list[dt.date] = DAYS) -> dict[dt.date, bool]:
    return {d: bool(v) for d, v in zip(days, values, strict=True)}


def synthetic(
    p_a: float, p_b: float, rho_copy: float, seed: int
) -> tuple[dict[dt.date, bool], dict[dt.date, bool]]:
    """b copies a on a share ``rho_copy`` of days (positive correlation), else independent."""
    rng = np.random.default_rng(seed)
    a = rng.random(365) < p_a
    b_ind = rng.random(365) < p_b
    copy = rng.random(365) < rho_copy
    # keep b's marginal rate near p_b when copying a: copy a only where it doesn't push b off
    b = np.where(copy, a & (rng.random(365) < p_b / p_a), b_ind)
    return outcomes(a), outcomes(b)


def test_recovers_known_difference() -> None:
    a, b = synthetic(0.85, 0.60, 0.0, seed=1)
    diff = sum(a.values()) / 365 - sum(b.values()) / 365
    low, high = paired_bootstrap(a, b, 10_000, 0.95, seed=7, key="x")
    assert low < diff < high
    assert low > 0


def test_independent_case_close_to_closed_form() -> None:
    a, b = synthetic(0.80, 0.70, 0.0, seed=2)
    pa, pb = sum(a.values()) / 365, sum(b.values()) / 365
    half = 1.959964 * math.sqrt(pa * (1 - pa) / 365 + pb * (1 - pb) / 365)
    low, high = paired_bootstrap(a, b, 10_000, 0.95, seed=7, key="x")
    assert (high - low) == pytest.approx(2 * half, rel=0.12)


def test_positive_correlation_gives_narrower_interval() -> None:
    a, b_ind = synthetic(0.80, 0.70, 0.0, seed=3)
    _, b_cor = synthetic(0.80, 0.70, 0.9, seed=3)
    lo_i, hi_i = paired_bootstrap(a, b_ind, 10_000, 0.95, seed=7, key="x")
    lo_c, hi_c = paired_bootstrap(a, b_cor, 10_000, 0.95, seed=7, key="x")
    w_ind, w_cor = hi_i - lo_i, hi_c - lo_c
    assert w_cor < 0.8 * w_ind


def test_same_seed_and_key_identical_different_key_independent() -> None:
    a, b = synthetic(0.8, 0.7, 0.0, seed=4)
    first = paired_bootstrap(a, b, 2_000, 0.95, seed=7, key="pair-1")
    assert paired_bootstrap(a, b, 2_000, 0.95, seed=7, key="pair-1") == first
    assert paired_bootstrap(a, b, 2_000, 0.95, seed=7, key="pair-2") != first


def test_dates_where_only_one_itinerary_has_an_outcome() -> None:
    a = {d: True for d in DAYS[:200]} | {d: False for d in DAYS[200:300]}
    b = {d: False for d in DAYS[100:365]}
    low, high = paired_bootstrap(a, b, 2_000, 0.95, seed=7, key="x")
    assert 0 < low <= high <= 1


def test_no_overlap_or_empty_returns_none() -> None:
    assert _paired_bootstrap({}, {DAYS[0]: True}, 1_000, 0.95, seed=7, key="x") == (None, None)


def test_parallel_bootstraps_equal_sequential(monkeypatch: pytest.MonkeyPatch) -> None:
    from flight_pipeline.compare import BootstrapTask, paired_bootstraps
    from flight_pipeline.storage import THREADS_ENV

    start = dt.date(2024, 7, 1)
    tasks: list[BootstrapTask] = []
    for i in range(140):
        a = {start + dt.timedelta(d): (d * 7 + i) % 5 != 0 for d in range(60)}
        b = {start + dt.timedelta(d): (d * 3 + i) % 4 != 0 for d in range(5, 70)}
        tasks.append((a, b, 200, 0.95, 7, f"pair{i}"))
    monkeypatch.setenv(THREADS_ENV, "2")
    assert paired_bootstraps(tasks) == [paired_bootstrap(*t) for t in tasks]
