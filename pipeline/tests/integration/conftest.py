"""Shared setup for end-to-end tests: a synthetic year and a config pointing at it."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from flight_pipeline.cli import main
from tests.integration.synthetic import write_year

REPO = Path(__file__).resolve().parents[3]

# Overrides for the synthetic world (8-airport pool, small resample count for speed).
OVERRIDES = {
    "candidate_pool_size": "8",
    "eligible_itineraries_min": "5",
    "count": "5",
    "max_pairs_per_hub": "15",
    "od_pairs_count": "10",
    "bootstrap_resamples": "2000",
}


def make_config(root: Path, raw: Path) -> Path:
    text = (REPO / "config" / "phase1.toml").read_text(encoding="utf-8")
    for key, value in OVERRIDES.items():
        text, n = re.subn(rf"^{key} = .*$", f"{key} = {value}", text, flags=re.MULTILINE)
        assert n == 1, key
    text = text.replace('raw_dir = "data/raw"', f'raw_dir = "{raw.as_posix()}"')
    text = text.replace(
        'derived_dir = "data/derived/phase1"', f'derived_dir = "{(root / "derived").as_posix()}"'
    )
    text = text.replace(
        'reports_dir = "reports/phase1"', f'reports_dir = "{(root / "reports").as_posix()}"'
    )
    text = text.replace(
        'manual_file = "data/raw/t100/t100_segment.csv"',
        f'manual_file = "{(raw / "t100" / "t100_segment.csv").as_posix()}"',
    )
    # The synthetic files are not the pinned BTS files.
    for section, following in (
        ("[sources.ontime.checksums]", "[sources.db1b]"),
        ("[sources.db1b.checksums]", "[sources.t100]"),
    ):
        start = text.index(section)
        end = text.index(following)
        text = text[:start] + section + "\n\n" + text[end:]
    text = text.replace(
        text[text.index('checksum = "') : text.index("\n", text.index('checksum = "'))],
        'checksum = ""',
    )
    path = root / "config" / "phase1.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture(scope="session")
def synthetic_raw(tmp_path_factory: pytest.TempPathFactory) -> Path:
    raw = tmp_path_factory.mktemp("synthetic") / "raw"
    write_year(raw)
    return raw


@pytest.fixture
def run_root(tmp_path: Path, synthetic_raw: Path) -> tuple[Path, Path]:
    """(root, config path) for one isolated run over the shared synthetic raw data."""
    raw = tmp_path / "raw"
    shutil.copytree(synthetic_raw, raw)
    return tmp_path, make_config(tmp_path, raw)


STAGES = ["prepare", "select-hubs", "build", "analyze", "report"]


@pytest.fixture(scope="session")
def finished(tmp_path_factory: pytest.TempPathFactory, synthetic_raw: Path) -> Path:
    """One full run (every stage after acquire), shared by the end-to-end tests."""
    root = tmp_path_factory.mktemp("e2e")
    raw = root / "raw"
    shutil.copytree(synthetic_raw, raw)
    config = make_config(root, raw)
    for stage in STAGES:
        assert main([stage, "--config", str(config)]) == 0, stage
    return root
