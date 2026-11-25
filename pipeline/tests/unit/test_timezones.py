"""Airport time-zone provider (ADR-0011, FR-004)."""

import pytest

from flight_pipeline.config import TimezoneOverride
from flight_pipeline.providers.timezones import (
    AirportsDataTimezones,
    MissingTimezoneError,
    airports_from_lookup,
)


def test_known_airports_return_iana_names() -> None:
    tz = AirportsDataTimezones({}).lookup(["ORD", "DEN", "PHX", "HNL", "JFK"])
    assert tz["ORD"].tz == "America/Chicago"
    assert tz["DEN"].tz == "America/Denver"
    assert tz["PHX"].tz == "America/Phoenix"
    assert tz["HNL"].tz == "Pacific/Honolulu"
    assert tz["JFK"].tz == "America/New_York"
    assert tz["ORD"].source.startswith("airportsdata")


def test_override_takes_precedence_and_records_source() -> None:
    provider = AirportsDataTimezones(
        {"ORD": TimezoneOverride(tz="America/New_York", source="test override")}
    )
    entry = provider.lookup(["ORD"])["ORD"]
    assert entry.tz == "America/New_York"
    assert entry.source == "test override"


def test_override_fills_missing_airport() -> None:
    provider = AirportsDataTimezones(
        {"QQQ": TimezoneOverride(tz="America/Chicago", source="FAA chart supplement")}
    )
    assert provider.lookup(["QQQ"])["QQQ"].tz == "America/Chicago"


def test_missing_airports_listed_in_error() -> None:
    with pytest.raises(MissingTimezoneError) as excinfo:
        AirportsDataTimezones({}).lookup(["ORD", "QQZ", "QQY"])
    assert excinfo.value.missing == ["QQY", "QQZ"]
    assert "QQY" in str(excinfo.value)
    assert "QQZ" in str(excinfo.value)


def test_airport_entities_populate_tz() -> None:
    lookup = AirportsDataTimezones({}).lookup(["ORD", "CMH"])
    airports = airports_from_lookup(lookup)
    assert [a.code for a in airports] == ["CMH", "ORD"]
    assert airports[1].tz == "America/Chicago"
    assert all(a.role == "other" for a in airports)


def test_time_zone_rules_come_from_the_pinned_tzdata_package() -> None:
    import zoneinfo

    import flight_pipeline  # noqa: F401  (importing the package sets the search path)

    # No system tz database is searched, so zoneinfo falls back to the tzdata package on
    # every operating system and the manifest's tzdata version describes the rules used.
    assert zoneinfo.TZPATH == ()
