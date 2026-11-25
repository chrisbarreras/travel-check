# ADR-0013: Itineraries must be sold routings that actually connect

- **Status:** Accepted (2026-11-24, with spec amendment 1 of feature 001). Supersedes rule 3 (recurrence) of [ADR-0004](0004-itinerary-definition.md) and adds a rule; ADR-0004's other rules stand.
- **Date:** 2026-11-24

## Context

ADR-0004 defined an itinerary by marketing airline (or a partner pair), layover limits, and each flight recurring on at least 60% of days. The Phase 0 analysis and its independent review ([specs/001/review.md](../../specs/001-bts-connection-experiment/review.md), rounds 4–5) showed two gaps:

- **Realism.** Nothing stops routings no traveler would choose. In 180 of 209 showcase examples, even the faster itinerary took more than 1.5 times the nonstop time.
- **Recurrence.** Two flights can each run on most days yet connect on only a few of them, for example 15% of days for one BOS-SFO itinerary.

A travel-time cap (such as 1.5 times the nonstop) was considered, but its threshold is a guess, and it doesn't say whether anyone buys the routing.

## Decision

1. **Sold routing.** An itinerary qualifies only if its routing appears in the BTS Airline Origin and Destination Survey (DB1B, a 10% ticket sample) with at least a configured minimum number of sampled passengers over the period (default 30). The routing is defined by:
   - the origin, connecting hub and destination of a directional trip with exactly one connection;
   - the airline that sold each of the two legs.

   The selling airlines must be the same marketing airline or a listed partner pair. They are matched to the on-time data's marketing airlines through a configured code mapping. Legs with no recorded selling airline are not counted.
2. **Connection-level recurrence** (replaces ADR-0004 rule 3). An itinerary qualifies only if its two flights connect on at least the recurrence threshold share of days in the period. A day connects when an outbound flight is scheduled within the layover limits after that day's scheduled inbound arrival. Cancelled flights count as scheduled.
3. **One period for all sources.** On-time, T-100 and DB1B data cover the same 12 months, in whole quarters. This is the latest period for which all three are published.

## Consequences

- Itineraries are on routings people buy, and actually work on most days, so the explorer won't show detours or itineraries that rarely connect. DB1B counts passengers per routing, not per flight, so every flight pair on a sold routing shares its count; the report shows how many itineraries share each routing.
- DB1B is published about 15 months after the quarter ends, so the analysis period is older than the latest on-time data. Phase 0 uses July 2024 to June 2025.
- DB1B adds a source behind a provider interface (Principle VI), about 110 MB zipped per quarter, with checksums pinned.
- The minimum passenger count is a new configured threshold. It is documented in the methodology, and excluded itineraries are counted per rule.
- DB1B also contains fares. They stay out of scope.
