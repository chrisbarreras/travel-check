# Feature Specification: Showcase Data Pipeline

**Feature Branch**: `002-showcase-data-pipeline`

**Created**: 2026-11-25

**Status**: Draft

**Input**: User description: "Phase 1 feature showcase-data-pipeline from docs/roadmap.md (feature short name: showcase-data-pipeline). A Python pipeline, extending the Phase 0 flight_pipeline, that precomputes curated showcase itineraries and their statistics into static JSON for the Phase 1 explorer, validated against Pydantic models that the future API will reuse (ADR-0007), with TypeScript types generated from them (CI fails when they are stale). It must carry the Phase 0 requirements from ADR-0012: identify itineraries by schedule (airline, route and departure-time window), not only by flight number, so airlines that renumber flights such as Southwest are covered; apply the layover limits only through the daily schedule matching; report travel time against the median nonstop time; prefer cross-hub showcase examples and keep any one market from dominating; use a stricter definition of regional origin (outside the candidate pool). Per curated itinerary it outputs per-day slack distributions for the browser transfer-time slider (ADR-0006) and the traveler-insight data in docs/roadmap.md Phase 1: faster alternatives with connection feasibility shown by the paired confidence interval to be no more than a configured margin worse (equivalence test, 60-minute comparability cap lifted for this comparison), which connecting flight to take at the hub, buffer recommendation (layover needed to have connected on a configured share of days), failure-type breakdown, monthly view with disruption events as separate labelled notes, schedule-pattern warnings, and the parameters for a Find this itinerary deep link. Every number keeps its definition, sample size and data period (constitution Principle I); wording is historical, never predictive. Data stays the pinned free BTS sources (on-time, DB1B, T-100) for July 2024 to June 2025, reproducible with verify. Out of scope: the frontend itself (web-foundation, explorer-core, explorer-insights), API, arbitrary route search and paste parsing (Phase 2), live data, fares, recovery routing, model calibration (Phase 3)."

## Context

Phase 0 showed that comparable itineraries can differ by 15–40 points in how often their connection worked (ADR-0012, decision GO). It also found weaknesses the explorer must not inherit: itineraries identified by flight number leave Southwest out entirely and underrepresent American; the layover rule used separate pattern medians as a pre-filter; slow routings were not compared with the nonstop; and the examples concentrate in Delta markets through Atlanta. This feature produces the data the Phase 1 explorer shows, fixes those weaknesses, and adds the traveler insights recorded in the roadmap and drawn in the mockup (`docs/design.md`).

The people who use this feature's output are the **explorer's developers** (the next three Phase 1 features build on it), the **travelers and reviewers** who will see the numbers on the site, and the **maintainer**, who reruns and verifies the data.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Itineraries that reflect how airlines actually fly (Priority: P1)

As a traveler or reviewer, I want the explorer's itineraries to represent real, regularly flown connections across all major airlines, including those that change flight numbers often, so that the comparisons are fair and not limited to a few airlines.

**Why this priority**: every number the explorer shows depends on how an itinerary is defined. Phase 0's flight-number identity leaves out Southwest and most American connections, so fixing identity comes before anything is shown.

**Independent Test**: run the pipeline on the reference fixtures and on the real data period, and check that an airline which renumbers its flights from day to day (a fixture case built for this) produces qualifying itineraries, that layover limits are applied only to each day's actual schedule, and that every itinerary reports its travel time against the nonstop.

**Acceptance Scenarios**:

1. **Given** an airline that flies the same two flights between the same airports at nearly the same times every day but under different flight numbers on different days, **When** itineraries are built, **Then** those days form one itinerary identified by airline, route and departure-time window, and it qualifies under the same rules as any other itinerary.
2. **Given** an itinerary whose flights change schedule at different times during the period, **When** its layover is checked, **Then** the layover limits are applied to each day's scheduled layover, and the itinerary is never excluded by a comparison of separate typical times.
3. **Given** an origin/destination pair with nonstop flights, **When** an itinerary on it is reported, **Then** it states its scheduled travel time and how that compares with the pair's typical nonstop time; **given** no nonstop, it says so.
4. **Given** the same identity rules applied to the full data period, **When** the pipeline reports itineraries per airline, **Then** every major network (American, Delta, United, Southwest, Alaska) that sells connections through the selected hubs has itineraries, or the report names it and says why not.

---

### User Story 2 - A curated, balanced showcase (Priority: P1)

As a reviewer opening the explorer, I want a small set of routes and examples that show the project's point clearly and fairly, so that I understand within seconds that similar-looking connections differ in how often they work.

**Why this priority**: Phase 1 is a curated showcase, not a search engine. Which routes and examples appear, and how they are balanced, decides whether the demo is convincing and honest.

**Independent Test**: run the curation on the real data period and check the selected routes and examples against the balance and selection rules, and that one landing example is chosen with the reasons recorded.

**Acceptance Scenarios**:

1. **Given** the analysis results, **When** the showcase is curated, **Then** it selects a configured number of origin/destination routes and, for each, its qualifying itineraries and showcase comparisons, preferring comparisons through different hubs.
2. **Given** that one market has far more showcase comparisons than others, **When** the showcase is curated, **Then** no single route, airline or hub exceeds its configured share of the showcase, and the report states the shares.
3. **Given** the candidate routes, **When** routes are marked as having a regional origin, **Then** only origins outside the candidate hub pool count as regional.
4. **Given** the curated set, **When** the landing example is chosen, **Then** it is a cross-hub comparison with a large, robust difference and no tight layover on the lower itinerary, and the selection reason is recorded with it.

---

### User Story 3 - Data the explorer can trust and use directly (Priority: P1)

As an explorer developer, I want the showcase data delivered as static files whose shapes are defined once and checked, with matching type definitions for the frontend, so that the site can be built without guessing and cannot silently drift from the data.

**Why this priority**: the next three Phase 1 features build on this output. A single definition of every shape (constitution Principle IV, ADR-0007) prevents the pipeline and the site from drifting apart.

**Independent Test**: generate the showcase files and the frontend type definitions; validate every file against its definitions; change a definition without regenerating and confirm the automated check fails.

**Acceptance Scenarios**:

1. **Given** a pipeline run, **When** the showcase files are written, **Then** every file validates against its single shape definition, and a file that does not validate stops the run with a clear message.
2. **Given** the shape definitions, **When** the frontend type definitions are generated, **Then** they correspond exactly to the definitions, and the automated checks fail whenever the committed type definitions are out of date.
3. **Given** any rate in the files, **When** it is read, **Then** it carries its sample size and data period, and a rate below the minimum sample is replaced by an explicit "insufficient data" state, never a number.

---

### User Story 4 - What-if transfer time in the browser (Priority: P2)

As a traveler, I want to move a transfer-time slider and see how often the connection would have worked with that much time needed, so that I can judge the connection for my own situation (checked bags, a slow walk, a tight airport).

**Why this priority**: this is the explorer's signature interaction (ADR-0006), but it depends on the itineraries and the data contract above.

**Independent Test**: for a fixture itinerary with hand-computed daily slack, check that the stored daily values reproduce, for any transfer time, the same feasibility rate the pipeline itself computes.

**Acceptance Scenarios**:

1. **Given** a curated itinerary, **When** its data is written, **Then** it includes each paired day's actual slack and outcome category, so that the share of days with at least a given amount of slack can be computed for any transfer time.
2. **Given** a transfer time equal to the default assumption, **When** the rate is recomputed from the stored daily values, **Then** it equals the pipeline's own default rate exactly.
3. **Given** days that were cancelled or diverted, **When** the slider changes, **Then** those days stay counted as failures and are reported separately, whatever the transfer time.

---

### User Story 5 - Traveler insights for each itinerary (Priority: P2)

As a traveler, I want each itinerary to come with practical, evidence-based guidance (a faster option that is just as reliable, a better connecting flight, the buffer I would have needed, why it failed, how it varied by month, and schedule warnings), so that I can choose a better connection, not just read a rate.

**Why this priority**: these insights turn the showcase from a chart into advice, and every one of them is supported by the Phase 0 data, but they are only meaningful once the itineraries and the data contract exist.

**Independent Test**: on the reference fixtures, check each insight against hand-computed values, including the cases where no insight applies.

**Acceptance Scenarios**:

1. **Given** a comparable itinerary that is meaningfully shorter, **When** faster alternatives are computed, **Then** it is listed only if the paired confidence interval shows its connection feasibility is no more than the configured margin worse, with the time saved, both rates, the interval and the shared days; the 60-minute travel-time limit of ordinary comparability does not apply to this comparison.
2. **Given** an inbound flight with several possible connecting flights at the hub, **When** connecting options are computed, **Then** they are ranked by connection feasibility with sample sizes, and a better option is offered only when its difference is significant under the same interval method.
3. **Given** an itinerary's daily slack, **When** the buffer recommendation is computed, **Then** it states the scheduled layover that would have connected on the configured share of operated days, and the itinerary's actual layover.
4. **Given** an itinerary's failed days, **When** they are summarized, **Then** the counts of too little time, cancellation and diversion are reported separately, with which one dominates.
5. **Given** the period, **When** the monthly view is computed, **Then** each month has its rate and sample, months without flights are marked as such, and known disruption events appear as separately labelled notes with a source, never mixed into the measured values.
6. **Given** an itinerary whose flights connect on fewer than all days, or whose schedule changed during the period, **When** warnings are computed, **Then** the share of connecting days and each schedule change (date and what changed) are reported.
7. **Given** a curated itinerary, **When** its data is written, **Then** it includes what a "Find this itinerary" link needs: origin, destination, marketing airline, the flight numbers used most often, and how many of the days they cover; no fare data is fetched or stored.

---

### User Story 6 - Reproducible, verifiable showcase data (Priority: P3)

As the maintainer, I want to rebuild the showcase data from the pinned sources with one command and verify it matches the committed files exactly, so that every number on the site traces back to the pipeline (Phase 1 exit criterion).

**Why this priority**: it extends the Phase 0 reproducibility guarantee to the new outputs; it is essential before deployment but builds on all the stories above.

**Independent Test**: run the full pipeline twice from the same pinned inputs and compare all outputs byte for byte; edit one committed showcase file by hand and confirm the verification fails.

**Acceptance Scenarios**:

1. **Given** the pinned configuration and sources, **When** the pipeline runs twice, **Then** every output, including the showcase files and type definitions, is byte-identical.
2. **Given** the committed showcase files, **When** verification runs, **Then** it reruns every stage and reports any file that differs, including a hand edit.
3. **Given** a run, **When** it finishes, **Then** a manifest records the sources, configuration, code version and runtime that produced the files.

---

### Edge Cases

- An airline renumbers only some days, or flies two different schedules under one number on the same day: identity follows the schedule window, and each day belongs to at most one itinerary.
- Two daily schedules of the same airline and route fall within one departure-time window: they are kept apart when their departure times are distinct on the same day.
- A connection's outbound leaves after the last loaded day of the period: that day is excluded from the connecting-day count rather than counted as not connecting (Phase 0 follow-up).
- An itinerary falls below the minimum sample in some months: those months show "insufficient data", not a rate.
- No faster alternative, better connecting flight or schedule warning applies: the data says so explicitly, so the explorer can show "none" rather than an empty space.
- A disruption event note has no reliable public source: it is not included.
- A curated route has no nonstop: travel-time comparison states that there is none.
- A selling airline in the ticket data is not a marketing airline in the on-time data: it is reported, as in Phase 0.
- The showcase files grow beyond the size budget: the run fails with the size reached, rather than shipping a slow site.

## Requirements *(mandatory)*

### Functional Requirements

**Itinerary identity and rules (ADR-0012)**

- **FR-001**: The pipeline MUST identify an itinerary by marketing airline (or listed partner pair), origin, connecting hub, destination and the inbound flight's scheduled departure-time window, not by flight number; each flown day belongs to at most one itinerary.
- **FR-002**: The pipeline MUST apply the layover limits (hub minimum, partner minimum, maximum) only to each day's scheduled layover in the daily schedule matching, with no pre-filter on separate typical times.
- **FR-003**: The pipeline MUST keep the Phase 0 rules for sold routings (DB1B, minimum sampled passengers) and connection-level recurrence (share of days the flights connect), and MUST count a day whose outbound falls after the loaded data as excluded, not as not connecting.
- **FR-004**: The pipeline MUST report, per itinerary, its typical scheduled travel time, the origin/destination pair's typical nonstop time (or that there is none), and the ratio between them.
- **FR-005**: The pipeline MUST report itineraries and sold passengers per marketing airline, and name every major network without itineraries with the reason.
- **FR-006**: The pipeline MUST define a regional origin as an origin outside the candidate hub pool.

**Curation**

- **FR-007**: The pipeline MUST select a configured number of showcase routes and, for each, its qualifying itineraries and showcase comparisons, preferring comparisons through different hubs.
- **FR-008**: The pipeline MUST cap the share of the showcase taken by any single route, airline and hub at configured limits, and report the resulting shares.
- **FR-009**: The pipeline MUST choose one landing example (a cross-hub comparison with a large, robust difference and no tight lower layover) and record the selection reason.
- **FR-010**: Showcase comparisons MUST meet the Phase 0 showcase rule (comparable, both with sufficient data on enough shared dates, not reversed by any assumption scenario, difference at least the threshold with a confidence interval excluding zero).

**Data contract**

- **FR-011**: Every output file MUST have one shape definition, shared with the future API (ADR-0007), and MUST be validated against it when written; a file that fails validation MUST stop the run.
- **FR-012**: Frontend type definitions MUST be generated from those shape definitions and committed, and the automated checks MUST fail when they are out of date.
- **FR-013**: Every rate MUST carry its written definition (by reference), sample size and data period; a rate below the minimum sample MUST be an explicit "insufficient data" state.
- **FR-014**: Wording and field names MUST describe historical frequencies ("worked on X% of days"), never predictions or passenger outcomes.
- **FR-015**: The showcase files MUST stay within a configured size budget, with the landing example's data loadable on its own.
- **FR-015a**: The showcase files MUST state their coverage: the routes, hubs, airlines and data period included, and the kinds of itinerary not covered (international legs, two or more stops, separate tickets, airlines that do not report on-time data, flights outside the data period), so the explorer can always say correctly that something is "not in the showcase" and why.

**Slack distributions (ADR-0006)**

- **FR-016**: Each curated itinerary MUST include each paired day's actual slack in whole minutes and its outcome category (operated, cancelled, diverted), sufficient to recompute feasibility for any transfer time, plus the default assumptions (minimum connection time, boarding cutoff).
- **FR-017**: A rate recomputed from the stored daily values at the default assumptions MUST equal the pipeline's own rate; the same calculation MUST be described by shared test cases that the explorer's in-browser version will also run (constitution Principle II).

**Traveler insights**

- **FR-018**: **Faster alternatives**: for each curated itinerary, list comparable itineraries (same origin and destination, departure within the departure window) that are shorter by at least a configured number of minutes and whose paired 95% confidence interval for the difference in feasibility has a lower bound no worse than the configured margin; report the time saved, both rates, the interval and the shared days. The 60-minute travel-time tolerance MUST NOT apply to this comparison.
- **FR-019**: **Connecting options**: for each curated inbound flight, rank the qualifying connecting flights at the hub to the same destination by feasibility with sample sizes, and flag a better option only when the paired interval excludes zero.
- **FR-020**: **Buffer**: report the scheduled layover that would have connected on the configured share of operated days, with the itinerary's actual scheduled layover.
- **FR-021**: **Failure types**: report failed days as too little time, cancelled and diverted, with the dominant type.
- **FR-022**: **Monthly view**: report each month's rate and sample (or "insufficient data" or "no flights"); disruption events MUST come from a curated, sourced list kept separate from measured values and appear only as labelled notes.
- **FR-023**: **Schedule warnings**: report the share of days the flights connect, and each schedule change during the period with its date and the change.
- **FR-024**: **Find this itinerary**: report the origin, destination, marketing airline and the most frequent flight numbers with the share of days they cover; no fare or availability data is fetched or stored.

**Reproducibility and operations**

- **FR-025**: The pipeline MUST be runnable end to end with one command from the pinned free sources (BTS on-time, DB1B and T-100, July 2024 to June 2025) and MUST produce byte-identical outputs on rerun.
- **FR-026**: Verification MUST rerun every stage and compare every output, including the showcase files and generated types, with the committed copies, reporting each difference.
- **FR-027**: The run manifest MUST record sources, configuration, code version, runtime and the machine it ran on; a runtime carried from an earlier run MUST only be kept when configuration, sources and code are unchanged.
- **FR-028**: Every new threshold (departure-time window, curation counts and shares, faster-alternative margin and minimum saving, buffer share, size budget) MUST be in the pinned configuration and documented in the methodology.

### Key Entities *(include if feature involves data)*

- **Itinerary**: a regular one-stop connection identified by airline (or partner pair), origin, hub, destination and departure-time window; has typical schedule, travel time, nonstop comparison, sold passengers on its routing, connecting-day share, and the flight numbers seen with their day shares.
- **Daily outcome**: one paired day of an itinerary: date, actual slack in minutes, and outcome category (feasible, too little time, cancelled, diverted).
- **Itinerary result**: connection feasibility with sample size, failure counts, slack percentiles and data period, at the default assumptions and per assumption scenario.
- **Showcase route**: an origin/destination pair chosen for the explorer, with its itineraries, its comparisons, whether its origin is regional, and its share of the showcase.
- **Showcase comparison**: a pair of comparable itineraries meeting the showcase rule, with difference, interval, shared days and settings compared.
- **Landing example**: the one comparison the explorer opens on, with its selection reason.
- **Traveler insight**: per itinerary, the faster alternatives, connecting options, buffer, failure breakdown, monthly view, schedule warnings and deep-link parameters, each with its evidence.
- **Disruption note**: a dated, sourced description of a known event (for example an outage or storm), shown beside measured values, never part of them.
- **Showcase manifest**: what produced the files (sources, configuration, code version, runtime) and the files' checksums.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every major network (American, Delta, United, Southwest, Alaska) has itineraries in the analysis, or the report names it with the reason; Southwest's count rises from 0 in Phase 0.
- **SC-002**: No single route supplies more than the configured share of showcase comparisons (default one third), and at least half of the showcase comparisons go through different hubs.
- **SC-003**: Every rate in the showcase files carries its sample size and data period, and no rate below the minimum sample appears as a number.
- **SC-004**: For every curated itinerary, the rate recomputed from its stored daily values at the default assumptions equals the pipeline's rate exactly.
- **SC-005**: Every faster alternative listed satisfies the equivalence rule, and every curated itinerary states explicitly when no faster alternative, better connecting flight or schedule warning applies.
- **SC-006**: Two runs from the same pinned inputs produce byte-identical outputs, and verification detects a one-byte hand edit in any committed showcase file.
- **SC-007**: The landing example's data loads in under 1 second on a typical mobile connection, and the full showcase stays within the configured size budget (default 2 MB compressed).
- **SC-008**: A full run, excluding downloads, finishes in under 30 minutes on a 4-core reference machine.
- **SC-009**: The automated checks fail within the same change whenever the committed frontend type definitions do not match the shape definitions.

## Out of Scope

- The explorer frontend itself: scaffold and tests (`web-foundation`), map, list and timeline (`explorer-core`), insight panels and slider UI (`explorer-insights`).
- An API, arbitrary route search, the browse and paste screens and pasted-text parsing (Phase 2).
- Live data, fares and ticketing, recovery routing, and model calibration or predictions (Phases 3–5).
- Time-of-day advice (backlog, until it can be tested per route).
- New data sources or periods beyond the pinned July 2024 – June 2025 BTS data.

## Assumptions

- The Phase 0 pipeline, sources, checksums and verification are reused and extended; Phase 0's committed results stay as the record of ADR-0012, and this feature writes its outputs separately.
- Hubs and routes are reselected with the new identity rules, so the curated set may differ from Phase 0's selected pairs; the showcase still has to meet the Phase 0 go criterion, and the change is reported.
- **Departure-time window**: an inbound flight's scheduled departure within 30 minutes of the itinerary's typical departure, configurable.
- **Curation size**: 8 to 12 showcase routes, with up to 12 itineraries per route, configurable.
- **Balance caps**: at most one third of showcase comparisons from any single route, and at most half from any single airline or hub, configurable.
- **Faster alternatives**: at least 15 minutes shorter; feasibility no more than 2 points worse at the lower bound of the 95% paired interval, configurable.
- **Buffer share**: 95% of operated days, configurable.
- **Size budget**: 2 MB compressed for all showcase files; the landing example loadable on its own.
- **Disruption notes**: a short hand-curated list (for example the July 2024 CrowdStrike outage), each entry with a date range, affected airlines or airports and a public source.
- The default assumptions stay those of Phase 0: 30-minute minimum connection time (45 for partners), 15-minute boarding cutoff, 60% recurrence, 30 sampled passengers.
- The reference machine for runtime is a 4-core, 16 GB machine, as in Phase 0.
