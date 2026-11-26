"""Determinism and the reproducibility check (SC-001, FR-033, research R8)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from flight_pipeline.cli import main
from tests.integration.conftest import make_config


def run_all(config: Path) -> None:
    assert main(["run", "--no-acquire", "--config", str(config)]) == 0


def test_two_runs_give_identical_outputs(
    tmp_path: Path, synthetic_raw: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifests = []
    for name in ("a", "b"):
        root = tmp_path / name
        raw = root / "raw"
        shutil.copytree(synthetic_raw, raw)
        run_all(make_config(root, raw))
        capsys.readouterr()
        manifests.append(json.loads((root / "reports" / "manifest.json").read_text()))
        assert (root / "reports" / "summary.json").exists()
    a, b = manifests
    assert a["outputs"] == b["outputs"]
    assert (tmp_path / "a" / "reports" / "summary.json").read_bytes() == (
        tmp_path / "b" / "reports" / "summary.json"
    ).read_bytes()


def test_verify_passes_on_unchanged_run_and_fails_on_a_change(
    run_root: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from flight_pipeline import schemas

    monkeypatch.setattr(schemas, "npx_generator", lambda schema: b"// stub types\n")
    root, config = run_root
    run_all(config)
    assert main(["schemas", "--config", str(config)]) == 0
    capsys.readouterr()
    assert main(["verify", "--config", str(config)]) == 0
    out, _ = capsys.readouterr()
    assert "identical" in out

    manifest_path = root / "reports" / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["outputs"]["comparable_pairs.parquet"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest))
    assert main(["verify", "--config", str(config)]) == 1
    _, err = capsys.readouterr()
    assert "comparable_pairs.parquet" in err
