"""Shared pytest configuration."""

from pathlib import Path

import pytest
from hypothesis import HealthCheck, settings

settings.register_profile(
    "deterministic",
    derandomize=True,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.load_profile("deterministic")

TESTS_DIR = Path(__file__).parent
FIXTURES = TESTS_DIR / "fixtures"
REPO_ROOT = TESTS_DIR.parent.parent


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT
