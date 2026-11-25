"""Airport -> IANA time zone, from the airportsdata package (ADR-0011)."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from functools import cache
from importlib.metadata import version

import airportsdata

from flight_pipeline.config import TimezoneOverride
from flight_pipeline.models import Airport
from flight_pipeline.providers.base import TimezoneEntry


class MissingTimezoneError(LookupError):
    """Raised when airports have no time-zone mapping (FR-004). The run must stop."""

    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        super().__init__(
            f"{len(missing)} airport(s) have no time-zone mapping: {', '.join(missing)}. "
            "Add each to [timezones.overrides] in the config with its IANA zone and source."
        )


@cache
def _iata_table() -> dict[str, str]:
    return {code: rec["tz"] for code, rec in airportsdata.load("IATA").items() if rec.get("tz")}


class AirportsDataTimezones:
    """TimezoneSource backed by airportsdata, with config overrides taking precedence."""

    def __init__(self, overrides: Mapping[str, TimezoneOverride]) -> None:
        self._overrides = dict(overrides)
        self._source = f"airportsdata {version('airportsdata')}"

    def lookup(self, codes: Iterable[str]) -> dict[str, TimezoneEntry]:
        table = _iata_table()
        out: dict[str, TimezoneEntry] = {}
        missing: list[str] = []
        for code in sorted(set(codes)):
            if code in self._overrides:
                o = self._overrides[code]
                out[code] = TimezoneEntry(tz=o.tz, source=o.source)
            elif code in table:
                out[code] = TimezoneEntry(tz=table[code], source=self._source)
            else:
                missing.append(code)
        if missing:
            raise MissingTimezoneError(missing)
        return out


def airports_from_lookup(lookup: Mapping[str, TimezoneEntry]) -> list[Airport]:
    """Airport entities with ``tz`` set; roles are assigned later by hub selection."""
    return [Airport(code=code, tz=lookup[code].tz, role="other") for code in sorted(lookup)]
