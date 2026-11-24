# ADR-0008: Store times in UTC; convert to local only for display

- **Status:** Accepted
- **Date:** 2026-11-24

## Context

BTS records times as local clock times (HHMM) with the flight date and no time zone. Arrivals can fall after midnight, BTS uses `2400` for midnight, and flights cross time zones and daylight-saving changes. Computing slack directly from local times gives wrong results for connections across midnight or time zones, which corrupts the risk numbers.

## Decision

- Keep an **airport time-zone table** that maps each airport to its IANA time zone (for example `America/Denver`), sourced from OpenFlights airport data, with attribution as its license requires.
- The pipeline converts every scheduled and actual time to **UTC** using the airport's time zone, handling `2400` and rolling the date forward when a time falls past midnight.
- All calculations, including slack, use UTC.
- Convert to **local airport time only for display**, and always show which airport's local time is meant.
- Tests cover midnight crossings, daylight-saving transitions, and connections across time zones.

## Consequences

- Slack and layover values are correct regardless of time zones and date boundaries.
- The time-zone table is a pipeline dependency and must cover every airport in the data; airports missing from it fail the pipeline loudly instead of being silently skipped.
