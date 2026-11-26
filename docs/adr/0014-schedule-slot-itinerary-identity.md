# ADR-0014: Identify itineraries by schedule slot; apply layover limits per day

- **Status:** Accepted (2026-11-25, with the approved plan of feature 002, `showcase-data-pipeline`). Supersedes the identity of an itinerary's flights in [ADR-0004](0004-itinerary-definition.md) and [ADR-0013](0013-sold-routings-and-connection-recurrence.md) (flight numbers), and how ADR-0004's layover rule is applied (median schedule). ADR-0004's airline-compatibility and limits, and ADR-0013's sold-routing and connection-recurrence rules, stand.
- **Date:** 2026-11-25

## Context

Phase 0 identified an itinerary's two flights by marketing airline and flight number, and checked the layover on each flight's median schedule. The Phase 0 decision record ([ADR-0012](0012-phase0-go-no-go.md)) and its independent review found two consequences:

- **Airlines that renumber flights are missing.** Southwest flies the same schedule under different flight numbers on different days, so almost none of its flight numbers recur on 60% of days: it had no itineraries, and American was heavily underrepresented.
- **Median schedules misstate layovers.** When two flights change schedule at different times of the year, the difference of their separate medians can be far from the layover actually flown, which mislabelled tight connections and excluded itineraries that connect.

## Decision

1. **Schedule slot.** A flight's identity is its marketing airline, origin, destination and a **schedule slot**: a cluster of scheduled local departure times within a configured window (default 30 minutes). Each flight-day belongs to exactly one slot. The flight numbers seen in a slot, and how often each was used, are kept for display and for "find this itinerary" links. Clustering uses local time of day, which stays stable across daylight-saving changes; every measured quantity stays in UTC (ADR-0008).
2. **Itinerary.** An itinerary is an inbound slot and an outbound slot through a hub, under ADR-0004's airline-compatibility rule.
3. **Layover limits per day.** The minimum and maximum layover apply only to each day's scheduled layover, in the same daily matching that counts connecting days (ADR-0013). A pre-filter may drop a candidate only when no combination of its slots' times can produce a layover within the limits, so it never excludes an itinerary that connects.
4. **Days at the end of the period** whose matching window runs past the loaded data are excluded from the connecting-day count, not counted as not connecting.

## Consequences

- Southwest's and American's regular connections can qualify; coverage per airline is reported.
- Itinerary IDs are built from slots (`{origin}-{hub}-{dest}:{airline}{HHMM}+{airline}{HHMM}`), not flight numbers, so they are not comparable with Phase 0's IDs.
- Phase 0's results are frozen at the git tag `phase0-final`; later code does not reproduce them.
- Reported layover and travel time are medians over connecting days.
- The daily matching runs on more candidates than Phase 0's median pre-filter allowed; the lossless bound pre-filter and the sold-routing rule keep it within the runtime budget.
- Departure minutes are clustered on the clock from 00:00 to 23:59, not around midnight: a flight scheduled at 23:55 on some days and 00:05 on others forms two slots, each of which may fall below the recurrence threshold. In the Phase 1 data, 59 same-airline, same-route slot pairs lie within 30 minutes of each other across midnight. Circular clustering is a candidate change for a later feature.
- Departure times that vary by day of week or season (Southwest's) split into many slots, so such airlines still have few itineraries; the report lists itineraries per airline.

## Amendment (implementation, 2026-11-26)

Joining works on runs: each sub-slot is cut at gaps longer than 7 days and the runs are joined across schedule changes, so a change and a change back (a seasonal schedule A, B, A) is one slot with both changes recorded. Runs of one sub-slot always stay together, and a join is made only when the two slots never fly on the same day (research R1 step 4).
