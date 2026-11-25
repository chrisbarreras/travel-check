# ADR-0011: Use the airportsdata package for airport time zones

- **Status:** Accepted (2026-11-24, with approval of the feature 001 plan). Supersedes the time-zone *source* in ADR-0008; the rest of ADR-0008 stands.
- **Date:** 2026-11-24

## Context

ADR-0008 named OpenFlights airport data as the source of airport time zones. Its maintainers describe the public copy as "a sporadically updated static snapshot," it is licensed under ODbL with attribution requirements, and it would have to be downloaded and versioned by hand.

## Decision

- Use the `airportsdata` Python package (MIT license), loaded keyed by IATA code, and its `tz` field, which holds IANA time zone names.
- Pin its version in the pipeline lockfile, so every run uses the same mapping.
- Any airport missing from it is filled from a small override table in configuration, with the source of each override recorded. Airports with no mapping still stop the pipeline (ADR-0008).

## Consequences

- Time-zone lookups are reproducible and come from a versioned, installable dependency.
- Upgrading the package is a deliberate change visible in the lockfile.
- The MIT license requires only that the license notice be kept, which is recorded in the report's attribution section.
