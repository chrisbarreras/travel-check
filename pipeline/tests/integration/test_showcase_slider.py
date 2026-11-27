"""SC-004: recomputing every published itinerary's rate from its daily series, at its
default transfer time, gives exactly the published result (ADR-0006, research R7)."""

from __future__ import annotations

from pathlib import Path

from flight_pipeline.showcase.models import RouteFile, ShowcaseIndex
from flight_pipeline.showcase.slider import recompute


def test_daily_series_reproduce_every_published_rate(finished: Path) -> None:
    out = finished / "site-data" / "showcase"
    idx = ShowcaseIndex.model_validate_json((out / "index.json").read_bytes())
    a = idx.assumptions
    checked = 0
    for summary in idx.routes:
        route = RouteFile.model_validate_json((out / summary.file).read_bytes())
        for it in route.itineraries:
            got = recompute(
                it.daily.slack_min,
                it.daily.outcome,
                it.min_connection_min,
                a.boarding_cutoff_min,
                a.min_sample_days,
            )
            assert got.paired_days == it.result.paired_days, it.itinerary_id
            assert got.count_feasible == it.result.count_feasible, it.itinerary_id
            assert got.status == it.result.status, it.itinerary_id
            assert got.rate == it.result.rate, it.itinerary_id
            assert all(0 <= d < 366 for d in it.daily.day_offset)
            checked += 1
    assert checked > 0


def test_a_longer_transfer_time_never_raises_the_rate(finished: Path) -> None:
    out = finished / "site-data" / "showcase"
    idx = ShowcaseIndex.model_validate_json((out / "index.json").read_bytes())
    a = idx.assumptions
    route = RouteFile.model_validate_json((out / idx.routes[0].file).read_bytes())
    for it in route.itineraries:
        counts = [
            recompute(
                it.daily.slack_min, it.daily.outcome, t, a.boarding_cutoff_min, 1
            ).count_feasible
            for t in range(0, 121, 15)
        ]
        assert counts == sorted(counts, reverse=True)
