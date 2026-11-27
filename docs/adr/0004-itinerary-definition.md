# ADR-0004: What counts as an itinerary

- **Status:** Accepted; recurrence rule superseded, and a sold-routing rule added, by [ADR-0013](0013-sold-routings-and-connection-recurrence.md); flight identity (flight numbers) and how the layover rule is applied (per day, not on median schedules) superseded by [ADR-0014](0014-schedule-slot-itinerary-identity.md)
- **Date:** 2026-11-24

## Context

BTS on-time data records flights that actually operated. It is not a bookable schedule and contains no tickets. The pipeline must therefore decide which pairs of flights count as a plausible one-stop connection. This definition affects every number in the app.

Constraints:

- **BTS covers only US domestic flights operated by US airlines**, so international itineraries cannot be built from it.
- Many flights from regional airports are **operated by regional airlines** (such as SkyWest, Republic or Envoy) on behalf of mainline brands, and one regional airline may fly for several brands. BTS (2018 onward) records both the marketing and the operating airline.
- Under common fare rules, a US domestic layover over 4 hours is a *stopover*, not a connection; international connections allow up to 24 hours.

## Decision

A one-stop itinerary is two legs (inbound to the hub, then outbound from it) that meet all of the following:

1. **Airline compatibility.** Both legs are sold by the **same marketing airline**, or by a pair listed in a configurable **partner table** that allows through-ticketing (for example, American and Alaska). Matching on *operating* airline is not allowed, because it would create itineraries no airline sells.
2. **Layover within limits.** The *scheduled* layover falls between a minimum and a maximum taken from configuration:

   | Setting | Domestic default | International (reserved for later) |
   |---|---|---|
   | Minimum | Per-airport assumed minimum connection time; default 30 min, 45 min for partner connections | Per airport, longer for immigration and customs |
   | Maximum | 4 h (stopover threshold) | 24 h |

3. **Recurring.** Both flight numbers operated on at least **60% of days** in the data period (configurable), which filters out one-off and irregular flights.

Partner itineraries are labeled "partner connection" in the UI, with a note that check-in and rebooking protection depend on how the ticket was sold.

International itineraries are out of scope until a data source for international legs is chosen; the configuration reserves the international settings.

## Consequences

- Itineraries correspond to connections an airline plausibly sells, including the regional flights typical of the target users.
- Results depend on configured assumptions (minimum connection times, partner table, recurrence threshold). These are recorded in the methodology, and Phase 0 tests how sensitive results are to them.
- Long layovers are kept in the data even if the UI shows fewer of them by default; they matter more for recovery options than for connection risk.
- The partner table needs occasional manual updates as airline partnerships change.
