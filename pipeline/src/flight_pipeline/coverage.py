"""Which airlines the itineraries come from (specs/002 FR-005)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from flight_pipeline.showcase.models import AirlineCoverage


def airline_coverage(
    itinerary_airlines: Sequence[str],
    sold_same_airline: Mapping[str, int],
    major_networks: Sequence[str],
    analysis_itineraries: Mapping[str, int] | None = None,
    routings_at_minimum: Mapping[str, int] | None = None,
    min_sold_passengers: int | None = None,
) -> list[AirlineCoverage]:
    """Per marketing airline: itineraries (by inbound airline) and sampled DB1B passengers
    on sold same-airline routings through the selected hubs. Every major network appears;
    one without itineraries carries a plain-language reason. When ``itinerary_airlines`` is
    a subset (the curated showcase), ``analysis_itineraries`` gives each airline's count in
    the whole analysis, so that an airline with itineraries but none in the subset says so.
    With ``routings_at_minimum`` (same-airline routings through the hubs that meet the
    sold-passenger minimum), an airline whose routings all fall below it says so. Sorted by
    sold passengers, then itineraries, then airline."""
    counts: dict[str, int] = {}
    for a in itinerary_airlines:
        counts[a] = counts.get(a, 0) + 1
    rows: list[AirlineCoverage] = []
    for a in set(counts) | set(sold_same_airline) | set(major_networks):
        n, sold = counts.get(a, 0), sold_same_airline.get(a, 0)
        note = ""
        overall = (analysis_itineraries or {}).get(a, 0)
        if n == 0 and overall > 0:
            note = (
                f"has {overall:,} itineraries through the selected hubs, none on the curated "
                "showcase routes"
            )
        elif (
            n == 0
            and sold > 0
            and routings_at_minimum is not None
            and routings_at_minimum.get(a, 0) == 0
        ):
            note = (
                "sells connections through the selected hubs, but no routing reaches the "
                f"minimum of {min_sold_passengers} sampled passengers"
            )
        elif n == 0 and sold > 0:
            note = (
                "sells connections through the selected hubs, but none of its schedules "
                "recur and connect regularly within the layover limits"
            )
        elif n == 0:
            note = "no sold connections through the selected hubs"
        rows.append(AirlineCoverage(airline=a, itineraries=n, sold_passengers=sold, note=note))
    return sorted(rows, key=lambda r: (-r.sold_passengers, -r.itineraries, r.airline))
