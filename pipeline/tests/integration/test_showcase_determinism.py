"""Reproducible showcase data (specs/002 User Story 6, FR-025, SC-006): two runs give the
same published files, and `verify` names every hand edit, stale type file and changed
input."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from flight_pipeline import schemas
from flight_pipeline.cli import main


def stub(schema: bytes) -> bytes:
    return b"// generated types for a schema of " + str(len(schema)).encode() + b" bytes\n"


def tree(root: Path) -> dict[str, bytes]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def full_run(config: Path) -> None:
    assert main(["run", "--no-acquire", "--config", str(config)]) == 0
    assert main(["schemas", "--config", str(config)]) == 0


@pytest.fixture(autouse=True)
def _no_node(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(schemas, "npx_generator", stub)


def test_two_runs_give_identical_published_files(
    run_root: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    # the same configuration run twice, from scratch each time
    root, config = run_root
    snapshots = []
    for _ in range(2):
        for d in ("derived", "reports", "site-data", "shared"):
            shutil.rmtree(root / d, ignore_errors=True)
        full_run(config)
        capsys.readouterr()
        published = tree(root / "site-data" / "showcase")
        manifest = json.loads(published.pop("manifest.json"))  # holds the run's time
        snapshots.append((published, tree(root / "shared"), manifest))
    (pa, sa, ma), (pb, sb, mb) = snapshots
    assert pa
    assert pa == pb
    assert sa == sb
    for key in ("outputs", "config_sha256", "notes_sha256", "sources", "packages", "code_version"):
        assert ma[key] == mb[key], key


def test_verify_names_every_changed_file_and_input(
    run_root: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    root, config = run_root
    full_run(config)
    capsys.readouterr()
    assert main(["verify", "--config", str(config)]) == 0
    assert "identical" in capsys.readouterr().out

    out = root / "site-data" / "showcase"
    route = sorted((out / "routes").glob("*.json"))[0]
    for path in (route, out / "index.json", root / schemas.TYPES_PATH):
        data = bytearray(path.read_bytes())
        data[-2] = ord(" ") if data[-2] != ord(" ") else ord("x")  # one byte, before the LF
        path.write_bytes(bytes(data))
    manifest = json.loads((out / "manifest.json").read_text())
    manifest["packages"]["duckdb"] = "0.0.0"
    (out / "manifest.json").write_text(json.dumps(manifest))
    config.write_text(config.read_text() + "\n# a changed configuration\n")

    assert main(["verify", "--config", str(config)]) == 1
    err = capsys.readouterr().err
    assert f"showcase/routes/{route.name}" in err
    assert "showcase/index.json" in err
    assert schemas.TYPES_PATH in err
    assert "showcase manifest packages differs" in err
    assert "config_sha256 differs" in err
