"""Shape definitions and generated types (specs/002 research R6, FR-012)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from flight_pipeline import schemas
from flight_pipeline.cli import main
from flight_pipeline.showcase.models import PUBLISHED_MODELS


def stub(schema: bytes) -> bytes:
    return b"// types for " + str(len(schema)).encode() + b"\n"


def test_schema_covers_every_published_model() -> None:
    defs = schemas.json_schema()["$defs"]
    for model in PUBLISHED_MODELS:
        assert model.__name__ in defs
    for nested in ("Rate", "DailySeries", "ShowcaseItinerary", "Coverage", "DisruptionNote"):
        assert nested in defs


def test_schema_bytes_are_stable_and_lf() -> None:
    first = schemas.schema_bytes()
    assert first == schemas.schema_bytes()
    assert b"\r" not in first
    assert json.loads(first)["title"] == "Showcase"


def test_check_reports_missing_stale_and_matching(tmp_path: Path) -> None:
    files = schemas.generate(stub)
    assert schemas.differences(tmp_path, files) == [
        f"{schemas.SCHEMA_PATH} is missing",
        f"{schemas.TYPES_PATH} is missing",
    ]
    schemas.write(tmp_path, files)
    assert schemas.differences(tmp_path, files) == []
    (tmp_path / schemas.TYPES_PATH).write_bytes(b"// edited\n")
    assert schemas.differences(tmp_path, files) == [
        f"{schemas.TYPES_PATH} differs from a fresh generation"
    ]


def _config(tmp_path: Path) -> Path:
    # a copy of the real config under a temporary repository root
    real = Path(__file__).resolve().parents[3] / "config"
    shutil.copytree(real, tmp_path / "config")
    return tmp_path / "config" / "phase1.toml"


def test_schemas_command_writes_then_check_passes_and_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(schemas, "npx_generator", stub)
    config = _config(tmp_path)
    assert main(["schemas", "--check", "--config", str(config)]) == 1
    assert main(["schemas", "--config", str(config)]) == 0
    assert main(["schemas", "--check", "--config", str(config)]) == 0
    (tmp_path / schemas.TYPES_PATH).write_bytes(b"// stale\n")
    assert main(["schemas", "--check", "--config", str(config)]) == 1
