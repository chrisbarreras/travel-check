# ADR-0005: Connection outcome label and same-day delay pairing

- **Status:** Accepted
- **Date:** 2026-11-24

## Context

No public dataset records whether passengers actually made their connections. BTS does record actual gate arrival and departure times, cancellations and diversions for each flight. Delays on the two legs of a connection are correlated: weather and congestion at the hub tend to affect both. Treating the legs as independent and multiplying their probabilities gives misleading results.

## Decision

**Outcome label.** For a historical day on which both legs were scheduled:

- *Raw slack* = outbound actual gate departure − inbound actual gate arrival.
- The connection is **feasible** if raw slack ≥ boarding cutoff + transfer time.
  - **Boarding cutoff**: the time before departure when boarding closes; configurable, default 15 minutes.
  - **Transfer time**: the time needed to move between gates; configurable, with defaults from [ADR-0004](0004-itinerary-definition.md).
- If either leg was **cancelled or diverted**, the connection is a failure, recorded separately from "too little time" so the two causes can be shown apart.

**Same-day pairing.** Connection risk is estimated from the *pairs of legs that actually operated on the same date*, never by combining each leg's delays independently. This keeps the effect of shared weather and congestion in the data.

**Wording.** The label measures *feasibility of the connection*, not observed passenger outcomes. The UI and methodology say so explicitly. It also cannot capture airlines holding a flight for connecting passengers, gate changes, or how full a flight is; these are listed as known limitations.

## Consequences

- The model can be checked against real historical outcomes, enabling holdout testing and calibration in Phase 3.
- The cutoff and transfer-time assumptions strongly affect results, so they stay adjustable and their sensitivity is reported.
- Same-day pairing needs enough recurring days per connection; small samples trigger fallback to broader groups or an "insufficient data" state.
