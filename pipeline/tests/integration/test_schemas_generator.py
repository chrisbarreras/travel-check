"""The real pinned TypeScript generator, and the committed shared/ files (FR-012)."""

from __future__ import annotations

import shutil

import pytest

from flight_pipeline import schemas
from tests.integration.conftest import REPO


@pytest.mark.skipif(shutil.which("npx") is None, reason="Node.js not available")
def test_real_generator_produces_types() -> None:
    ts = schemas.npx_generator(schemas.schema_bytes()).decode("utf-8")
    assert ts.startswith("/* Generated from shared/schemas/showcase.schema.json")
    assert "export interface ShowcaseIndex" in ts
    assert "export interface RouteFile" in ts
    assert "\r" not in ts


@pytest.mark.skipif(shutil.which("npx") is None, reason="Node.js not available")
def test_committed_files_are_current() -> None:
    # the same check CI runs: `flight-pipeline schemas --check`
    assert schemas.differences(REPO, schemas.generate()) == []
