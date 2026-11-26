"""Every published definition links to a real section of docs/methodology.md (FR-013, FR-028)."""

from __future__ import annotations

import re
from pathlib import Path

from flight_pipeline.showcase.publish import definitions

DOC = Path(__file__).resolve().parents[3] / "docs" / "methodology.md"


def github_anchor(heading: str) -> str:
    """GitHub's heading slug: lower case, punctuation other than hyphens and underscores
    removed, spaces as hyphens."""
    text = re.sub(r"[^\w\- ]", "", heading.strip().lower())
    return text.replace(" ", "-")


def test_github_anchor_rule() -> None:
    assert github_anchor("Connection feasibility (ADR-0005)") == "connection-feasibility-adr-0005"
    assert github_anchor("Phase 1: showcase data (feature `002-showcase-data-pipeline`)") == (
        "phase-1-showcase-data-feature-002-showcase-data-pipeline"
    )


def test_every_definition_anchor_exists() -> None:
    headings = [
        line.lstrip("#").strip()
        for line in DOC.read_text(encoding="utf-8").splitlines()
        if line.startswith("#")
    ]
    anchors = {github_anchor(h) for h in headings}
    for d in definitions():
        path, _, anchor = d.methodology_anchor.partition("#")
        assert path == "docs/methodology.md"
        assert anchor in anchors, d.key
