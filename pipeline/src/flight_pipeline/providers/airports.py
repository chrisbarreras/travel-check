"""Airport names and coordinates for the explorer map, from the airportsdata package
(ADR-0011; specs/004-explorer-core FR-001). Already attributed in every published index."""

from __future__ import annotations

from collections.abc import Iterable
from functools import cache
from typing import Any

import airportsdata

from flight_pipeline.showcase.models import AirportInfo


class MissingAirportError(LookupError):
    """Raised when a showcase airport has no airportsdata record. The run must stop."""

    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        super().__init__(f"no airportsdata record for {', '.join(missing)}")


@cache
def _iata() -> dict[str, Any]:
    return dict(airportsdata.load("IATA"))


def airport_infos(codes: Iterable[str]) -> list[AirportInfo]:
    """One record per distinct code, sorted by code."""
    table = _iata()
    wanted = sorted(set(codes))
    missing = [c for c in wanted if c not in table]
    if missing:
        raise MissingAirportError(missing)
    return [
        AirportInfo(
            code=code,
            name=str(table[code]["name"]),
            city=str(table[code]["city"]),
            lat=round(float(table[code]["lat"]), 6),
            lon=round(float(table[code]["lon"]), 6),
        )
        for code in wanted
    ]
