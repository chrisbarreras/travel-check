"""Origin/destination pair ranking and selection (FR-025, FR-018).

Candidates are pairs with at least two qualifying itineraries through the selected hubs,
ranked by their number of comparable itinerary pairs (FR-026), then origin, then destination.
The highest-ranked are taken up to the configured count, subject to: at least the configured
share have a regional (non-hub) origin, and at most the configured number of pairs per main
hub (the hub used by the largest share of the pair's itineraries).
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import duckdb

from flight_pipeline.config import Selection
from flight_pipeline.models import OdSelection


@dataclass(frozen=True)
class OdCandidate:
    origin: str
    dest: str
    itineraries: int
    comparable_pairs: int
    hub_counts: dict[str, int]

    @property
    def main_hub(self) -> str:
        return sorted(self.hub_counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def od_candidates(
    con: duckdb.DuckDBPyConnection, itineraries: str, comparable: str
) -> list[OdCandidate]:
    """Aggregate itineraries and comparable pairs by origin and destination."""
    hub_counts: dict[tuple[str, str], dict[str, int]] = {}
    for origin, dest, hub, n in con.execute(
        f"SELECT origin, dest, hub, count(*) FROM {itineraries} GROUP BY ALL"
    ).fetchall():
        hub_counts.setdefault((origin, dest), {})[hub] = int(n)
    pairs = {
        (r[0], r[1]): int(r[2])
        for r in con.execute(
            f"SELECT origin, dest, count(*) FROM {comparable} GROUP BY ALL"
        ).fetchall()
    }
    return [
        OdCandidate(
            origin=o,
            dest=d,
            itineraries=sum(h.values()),
            comparable_pairs=pairs.get((o, d), 0),
            hub_counts=h,
        )
        for (o, d), h in sorted(hub_counts.items())
    ]


def select_od_pairs(
    candidates: Sequence[OdCandidate],
    hubs: Iterable[str],
    cfg: Selection,
    *,
    pool: Iterable[str] | None = None,
) -> list[OdSelection]:
    """Rank and select pairs. A regional origin is one outside the candidate ``pool``
    (specs/002 FR-006); without a pool, outside the selected hubs (Phase 0's rule)."""
    outside = set(pool) if pool is not None else set(hubs)
    ranked = sorted(
        (c for c in candidates if c.itineraries >= 2),
        key=lambda c: (-c.comparable_pairs, c.origin, c.dest),
    )
    required_regional = math.ceil(cfg.regional_share_min * cfg.od_pairs_count)
    max_non_regional = cfg.od_pairs_count - required_regional
    per_hub: dict[str, int] = {}
    chosen = 0
    non_regional = 0
    out: list[OdSelection] = []
    for rank, c in enumerate(ranked, start=1):
        regional = c.origin not in outside
        take = (
            chosen < cfg.od_pairs_count
            and per_hub.get(c.main_hub, 0) < cfg.max_pairs_per_hub
            and (regional or non_regional < max_non_regional)
        )
        if take:
            chosen += 1
            per_hub[c.main_hub] = per_hub.get(c.main_hub, 0) + 1
            non_regional += 0 if regional else 1
        out.append(
            OdSelection(
                origin=c.origin,
                dest=c.dest,
                comparable_pairs=c.comparable_pairs,
                main_hub=c.main_hub,
                regional_origin=regional,
                rank=rank,
                selected=take,
            )
        )
    return out


def selection_shortfalls(rows: Sequence[OdSelection], cfg: Selection) -> list[str]:
    """Human-readable notes when the selection could not reach its targets."""
    chosen = [r for r in rows if r.selected]
    notes: list[str] = []
    if len(chosen) < cfg.od_pairs_count:
        notes.append(f"only {len(chosen)} of {cfg.od_pairs_count} pairs could be selected")
    regional = sum(r.regional_origin for r in chosen)
    if chosen and regional < math.ceil(cfg.regional_share_min * len(chosen)):
        notes.append(f"only {regional} of {len(chosen)} selected pairs have a regional origin")
    return notes


def pairs_without_itineraries(
    selected: Iterable[tuple[str, str]], available: set[tuple[str, str]]
) -> list[str]:
    """FR-018: selected pairs that have no qualifying itineraries (e.g. under a scenario)."""
    return [f"{o}-{d}" for o, d in selected if (o, d) not in available]
