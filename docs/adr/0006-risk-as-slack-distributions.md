# ADR-0006: Store risk as slack distributions, not single probabilities

- **Status:** Accepted
- **Date:** 2026-11-24

## Context

A single precomputed probability per connection fixes the transfer-time and boarding-cutoff assumptions at pipeline time. Users then can't adjust them, the UI can't show the spread of outcomes, and a static Phase 1 site can't recompute anything.

## Decision

For each connection, the pipeline stores the **distribution of raw slack**, as defined in [ADR-0005](0005-connection-outcome-label.md), over the data period:

- one raw-slack value per day on which both legs operated, kept sorted
- counts of days on which either leg was cancelled or diverted
- the sample size and data period

The probability of a feasible connection for any transfer time *T* and cutoff *C* is the share of days with raw slack ≥ *T* + *C*, with cancellations and diversions counted as failures. This is a simple lookup that runs in the browser (Phase 1) or in the API (Phase 2).

If file size becomes a problem as coverage grows, store fixed quantiles instead of every daily value. That change is a new ADR.

## Consequences

- A transfer-time slider is possible **in the static Phase 1 site**, not only once the API exists.
- Delay-distribution charts come from the same data, so visuals and numbers always agree.
- Data files are larger than with single probabilities, which is acceptable for the curated Phase 1 routes and is watched against the size budget in [ADR-0009](0009-data-storage-and-git.md).
- The browser and the API must use the same calculation, so it is specified once and tested on both sides with shared test cases.
