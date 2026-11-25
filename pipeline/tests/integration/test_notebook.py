"""The analysis notebook runs headlessly against pipeline outputs (Principle II)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

NOTEBOOK = Path(__file__).resolve().parents[3] / "notebooks" / "phase0_connection_experiment.py"


def test_notebook_runs_as_a_script(finished: Path) -> None:
    env = {
        **os.environ,
        "PHASE0_DERIVED": str(finished / "derived"),
        "PHASE0_REPORTS": str(finished / "reports"),
    }
    result = subprocess.run(
        [sys.executable, str(NOTEBOOK)],
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Traceback" not in result.stderr


def test_notebook_fails_loudly_without_outputs(tmp_path: Path) -> None:
    env = {**os.environ, "PHASE0_DERIVED": str(tmp_path), "PHASE0_REPORTS": str(tmp_path)}
    result = subprocess.run(
        [sys.executable, str(NOTEBOOK)],
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert result.returncode != 0
