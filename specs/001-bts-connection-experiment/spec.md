# Feature Specification: BTS Connection Feasibility Experiment

**Feature Branch**: `001-bts-connection-experiment`

**Created**: 2026-11-24

**Status**: Approved (amended by amendment 1, 2026-11-24)

**Input**: User description: "Phase 0 data feasibility check from docs/roadmap.md (feature short name: bts-connection-experiment). Using BTS on-time performance data for 5–8 US hubs over a few months, build one-stop itineraries per ADR-0004 (same marketing airline or listed partner pair; configurable layover limits with domestic defaults of a per-airport minimum, 30 min default / 45 min for partner connections, up to 4 h; both flights recurring on at least 60% of days), compute connection feasibility per ADR-0005 (raw slack from actual gate times, configurable boarding cutoff default 15 min, cancellations and diversions counted as failures and reported separately, same-day pairing of legs) for 10–15 origin/destination pairs including regional origins, and test how sensitive results are to the minimum connection time, boarding cutoff and recurrence threshold. Report sample sizes and flag cohorts below a minimum sample size as insufficient data. Output: a reproducible analysis (notebook backed by tested pipeline functions) and a written go/no-go finding recorded as a new ADR, identifying showcase examples where itineraries with similar price or duration differ meaningfully in connection feasibility. Times handled in UTC per ADR-0008; raw data out of git per ADR-0009. Out of scope: any UI, API, deployment, fares, live data, international routes, recovery routing, and model calibration (Phase 3)."

## Clarifications

### Session 2026-11-24

- Q: How large must the feasibility gap be for a showcase example, and how many examples are needed for a "go"? → A: A gap of at least 10 percentage points; at least 3 showcase examples across at least 2 hubs.
- Q: Should hubs be fixed or chosen from the data? → A: Chosen from the data, based on number of airlines, air traffic, weather situations and passenger volume. The data period is extended from 6 to 12 months so seasonal weather patterns can be measured.
- Q: How should the 10–15 origin/destination pairs be chosen? → A: From the data: ranked by number of comparable itinerary pairs, top 15 taken, at least half with regional origins, at most 3 pairs per hub.
- Q: Should comparable itineraries also leave at similar times of day? → A: Yes; scheduled departures from the origin must be within 3 hours of each other (configurable), in addition to travel times within 60 minutes.
- Q: Must a showcase example's 10-point gap also be statistically significant? → A: Yes; the 95% confidence interval for the difference in feasibility rates must exclude zero.
- Q: Which flights count as weather-affected for each hub's weather profile? → A: Flights with weather-attributed delay minutes, or cancelled for weather; National Aviation System delays are excluded.

### Session 2026-11-24 (amendment 1, after independent review rounds 4–5)

- Q: How do we know an itinerary is one travelers would actually choose? → A: Its routing (origin, connecting hub, destination and the airline that sold each leg) must appear in the BTS Airline Origin and Destination Survey (DB1B, a 10% ticket sample) with at least a minimum number of sampled passengers in the period.
- Q: What does "recurring" mean for an itinerary? → A: Its two flights must actually connect (a scheduled outbound flight within the layover limits after that day's inbound arrival) on at least the recurrence threshold share of days in the period; each flight running on most days separately is no longer enough.
- Q: Which period do the sources cover? → A: The same 12 months for all three sources, the latest for which all are published: July 2024 to June 2025 (DB1B is published later than the other sources).

## Purpose

Before any product is built, find out whether real historical flight data shows **meaningful differences in connection feasibility between itineraries a traveler would otherwise consider equivalent**. If it does, those differences become the showcase examples for Phase 1. If it doesn't, the project's central idea needs rethinking before more is invested.

The primary user is the project owner acting as analyst. Secondary readers are reviewers of the repository, who must be able to reproduce and audit every number.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Select hubs from the data (Priority: P1)

The analyst gets a set of hubs chosen by explicit, reproducible rules (airline diversity, air traffic, passenger volume and weather diversity) instead of by judgment, together with a report explaining why each hub was chosen.

**Why this priority**: hubs determine which itineraries exist and how representative the findings are. A documented, data-driven choice is what makes the results defensible.

**Independent Test**: run hub selection on a small, fixed reference set of airport metrics and confirm it selects exactly the expected hubs, in the expected order, with the expected reasons.

**Acceptance Scenarios**:

1. **Given** candidate airports with known airline counts, departures and passenger volumes, **When** hubs are selected, **Then** they are ranked by the documented score and the highest-scoring eligible airports are chosen, subject to the constraints below.
2. **Given** a major airline network whose only candidate hubs score below the cut-off, **When** hubs are selected, **Then** that network's highest-scoring eligible hub is included anyway, replacing the lowest-scoring hub not needed for any constraint.
3. **Given** a top-scoring set of hubs that all peak in weather-affected departures in the same season, **When** hubs are selected, **Then** the selection is adjusted so that both the winter-peak and summer-peak requirements are met.
4. **Given** a candidate airport offering fewer qualifying itineraries from regional origins than the eligibility minimum, **When** hubs are selected, **Then** it is ineligible regardless of its score.
5. **Given** constraints that can't all be satisfied, **When** hubs are selected, **Then** the report names each unmet constraint and the selection proceeds with the best available set.

---

### User Story 2 - Identify plausible one-stop itineraries (Priority: P1)

The analyst selects a set of origin/destination pairs, and gets the list of one-stop itineraries through the selected hubs that an airline plausibly sells between them, built from flights that actually operated.

**Why this priority**: every later result depends on itineraries being realistic. Itineraries no airline sells would make every finding meaningless.

**Independent Test**: run itinerary construction for one origin/destination pair on a small, fixed reference sample of flight records, and confirm the produced itineraries match a hand-checked expected list exactly.

**Acceptance Scenarios**:

1. **Given** two legs sold under the same marketing airline with a scheduled layover of 90 minutes, connecting on at least 60% of days in the period, and a routing sold to at least the minimum number of DB1B passengers, **When** itineraries are built, **Then** the pair is included as an itinerary.
2. **Given** two legs operated by the same regional airline but sold under different marketing airlines that are not a listed partner pair, **When** itineraries are built, **Then** the pair is excluded.
3. **Given** two legs sold by a listed partner pair, **When** itineraries are built, **Then** the pair is included and labeled as a partner connection, and the partner minimum layover (default 45 minutes) applies.
4. **Given** a scheduled layover below the hub's minimum or above 4 hours, **When** itineraries are built, **Then** the pair is excluded.
5. **Given** two flights that each run on most days but connect (outbound within the layover limits after that day's inbound) on fewer than 60% of days in the period, **When** itineraries are built, **Then** the itinerary is excluded and counted as below connection-level recurrence.
6. **Given** two legs that meet every other rule but whose routing has fewer than the minimum number of sampled DB1B passengers, **When** itineraries are built, **Then** the itinerary is excluded and counted as having no sold routing.

---

### User Story 3 - Measure connection feasibility with honest sample sizes (Priority: P1)

For each itinerary, the analyst sees how often the connection would have been feasible on the days both legs were scheduled, why it failed when it failed, and how many days the figure is based on.

**Why this priority**: this is the measurement the whole product rests on. Together with User Stories 1 and 2, it is the minimum useful result.

**Independent Test**: on the fixed reference sample, confirm each day's outcome (feasible, insufficient time, cancelled, diverted) and each itinerary's summary figures match hand-computed expected values, including cases that cross midnight, time zones and a daylight-saving change.

**Acceptance Scenarios**:

1. **Given** a day on which the inbound leg arrives at the gate 50 minutes before the outbound leg leaves the gate, with a 30-minute minimum connection time and 15-minute boarding cutoff, **When** the outcome is computed, **Then** the day is feasible (50 ≥ 30 + 15).
2. **Given** the same day with only 40 minutes between gate arrival and gate departure, **When** the outcome is computed, **Then** the day is classified as insufficient time.
3. **Given** a day on which either leg was cancelled, **When** the outcome is computed, **Then** the day is a failure classified as cancelled, counted separately from insufficient time.
4. **Given** a day on which either leg was diverted, **When** the outcome is computed, **Then** the day is a failure classified as diverted.
5. **Given** an itinerary with fewer paired days than the minimum sample size, **When** results are reported, **Then** the itinerary shows "insufficient data" and no feasibility rate.
6. **Given** an inbound arrival late in the evening and an outbound departure after midnight local time, **When** slack is computed, **Then** the result reflects the true elapsed time between the two events.

---

### User Story 4 - Test sensitivity to assumptions (Priority: P2)

The analyst reruns the measurements under different assumptions (minimum connection time, boarding cutoff, recurrence threshold) and sees which conclusions hold and which depend on the assumptions.

**Why this priority**: the assumptions are estimates, not measurements. A conclusion that flips when an assumption changes slightly is not safe to show users.

**Independent Test**: run the sensitivity analysis on the reference sample and confirm that each scenario's results match expected values, and that itineraries whose relative ranking changes between scenarios are flagged.

**Acceptance Scenarios**:

1. **Given** the default assumptions and a set of alternative values for each assumption, **When** the sensitivity analysis runs, **Then** feasibility rates are reported for every itinerary under every scenario.
2. **Given** two comparable itineraries whose order by feasibility reverses under some scenario, **When** results are reported, **Then** that pair is flagged as assumption-sensitive.

---

### User Story 5 - Record a go/no-go decision with showcase examples (Priority: P2)

The analyst gets a written finding that states whether the reliability differences are large enough to build the product on, lists the strongest showcase examples, and records it as a decision record.

**Why this priority**: the finding is the deliverable of Phase 0 and the gate into Phase 1.

**Independent Test**: confirm the decision record states the criteria, shows which were met, lists showcase examples that each satisfy the showcase definition, and lists known limitations.

**Acceptance Scenarios**:

1. **Given** completed measurements and sensitivity results, **When** the finding is written, **Then** it states the go/no-go criteria, whether each was met, and the resulting decision.
2. **Given** a candidate showcase example, **When** it is listed, **Then** both itineraries have sufficient data, are comparable in travel time and departure time, differ in feasibility by at least the showcase threshold with a 95% confidence interval that excludes zero, and are not flagged as assumption-sensitive.
3. **Given** two comparable itineraries whose rates differ by 12 points but whose 95% confidence interval for the difference includes zero, **When** showcase examples are selected, **Then** the pair is not a showcase example.

---

### User Story 6 - Reproduce the analysis from scratch (Priority: P3)

A reviewer with no prior setup rebuilds every result, including the hub selection, from the pinned configuration and gets identical numbers.

**Why this priority**: required by the constitution for trust and auditability, and it makes the project credible to reviewers, but it builds on the stories above.

**Independent Test**: delete all downloaded and derived data, rerun the full analysis from configuration, and confirm every reported number and the hub selection match the previous run exactly.

**Acceptance Scenarios**:

1. **Given** an empty data folder and the committed configuration, **When** the full analysis is run, **Then** all source data is obtained (automatically, except for a source with no scriptable download, whose manually downloaded file is accepted only if it matches the checksum pinned in configuration) and all results are regenerated identically.

---

### Edge Cases

- **Midnight and the `2400` time value:** a recorded time of `2400` and arrivals that fall on the next calendar day are converted to the correct instant.
- **Daylight-saving transitions:** slack spanning a daylight-saving change is computed from true elapsed time.
- **Time-zone crossings:** legs that cross time zones produce correct elapsed times.
- **Airport missing from the time-zone reference:** the analysis stops with an error listing the missing airports, rather than silently skipping flights.
- **Operated flight missing actual gate times:** the day is excluded from that itinerary's sample and counted in a data-quality tally.
- **Outbound departs on the next calendar day:** for layovers crossing local midnight, the outbound flight is matched on its correct service date.
- **Same flight number on several segments in one day:** flights are identified by marketing airline, flight number, service date and departure airport, so segments of the same flight number aren't confused.
- **Negative slack:** if the outbound leg left before the inbound leg arrived, the day is classified as insufficient time.
- **Duplicate records:** duplicates in the source data are detected and counted. When the copies are identical, one copy is kept; when copies of the same flight instance disagree, all copies are excluded.
- **No qualifying itineraries for an origin/destination pair:** the pair is reported as having no qualifying itineraries, not silently dropped.
- **Ties in hub score:** broken deterministically by airport code, so reruns select the same hubs.
- **Passenger data missing for a candidate airport:** the airport is ranked with the passenger component treated as zero and the gap is reported, rather than being silently dropped.
- **Routing missing from DB1B** (no sampled tickets, or below the minimum): the itinerary is excluded and counted (FR-018a), not judged by another rule.
- **Airline code not in the mapping:** a DB1B selling airline that is neither an on-time marketing airline nor mapped in configuration (for example a code retired by a merger) is reported; routings that use it are not counted.
- **Hub with no weather-affected departures in a season:** its seasonal weather profile is reported as unknown and it can't satisfy a seasonal weather constraint.

## Requirements *(mandatory)*

### Functional Requirements

**Data acquisition and preparation**

- **FR-001**: The system MUST obtain, for one configured 12-month period made of whole calendar quarters, the public US BTS on-time performance records, the BTS passenger traffic (T-100 segment) records and the BTS DB1B market records (Airline Origin and Destination Survey), using pinned configuration so the same inputs can be obtained again.
- **FR-002**: Raw source data MUST be stored outside version control (ADR-0009).
- **FR-003**: The system MUST convert every scheduled and actual time to an absolute UTC instant using each airport's time zone, correctly handling `2400`, times past local midnight and daylight-saving changes (ADR-0008).
- **FR-004**: The system MUST stop with an error listing any airport that lacks a time-zone mapping.
- **FR-005**: The system MUST detect and count duplicate records and operated flights missing actual gate times, and report the counts. Flights missing actual gate times are excluded from samples; duplicates are handled as described under Edge Cases.

**Hub selection**

- **FR-006**: The candidate pool MUST be the configured number of US airports with the most scheduled departures in the period (default 30).
- **FR-007**: For each candidate, the system MUST compute:
  - **Airline count:** the number of marketing airlines each accounting for at least a configured share (default 5%) of the airport's scheduled departures.
  - **Air traffic:** total scheduled departures.
  - **Passenger volume:** total passengers boarded (enplaned).
  - **Weather profile:** the share of scheduled departures that were weather-affected, overall and by season, and the season in which that share peaks. Seasons are winter (December–February), spring (March–May), summer (June–August) and autumn (September–November), configurable. A departure is weather-affected when it has weather-attributed delay minutes or was cancelled with weather as the reason. Delays attributed to the National Aviation System are excluded, because they mix weather with congestion.
- **FR-008**: A candidate MUST be eligible only if it offers at least a configured minimum number of qualifying itineraries (default 15) whose origin is outside the candidate pool, using the itinerary rules in FR-013 to FR-018.
- **FR-009**: Eligible candidates MUST be ranked by a hub score combining airline count, air traffic and passenger volume, each scaled to a 0–1 range across the candidate pool, with configurable weights (default equal weights).
- **FR-010**: The system MUST select a configured number of hubs (default 7, allowed range 5–8). Starting from the highest-scoring eligible candidates, it MUST adjust the selection, swapping in the next-best candidate that fixes a gap, so that:
  - **Airline coverage:** every major marketing airline network (default: American, Delta, United, Southwest, Alaska) with at least one eligible candidate has at least one selected hub where it is among the counted airlines.
  - **Weather diversity:** at least 2 selected hubs peak in winter (December–February) for weather-affected departures, at least 2 peak in summer (June–August), and the selection includes hubs both above and below the candidate pool's median overall weather-affected share.
- **FR-011**: When constraints can't all be met, the system MUST select the best available set and report each unmet constraint.
- **FR-012**: The system MUST produce a hub selection report listing every candidate's metrics, score, eligibility and rank, which hubs were selected, and the reason each was selected (score or a named constraint).

**Itinerary construction (ADR-0004)**

- **FR-013**: The system MUST pair an inbound leg (origin → hub) with an outbound leg (hub → destination) only when both legs are sold by the same marketing airline, or by a pair listed in a configurable partner table.
- **FR-014**: The system MUST NOT pair legs on the basis of operating airline.
- **FR-015**: The system MUST include a pair only when its scheduled layover is at least the configured minimum for the hub (default 30 minutes; 45 minutes for partner connections) and at most the configured maximum (default 4 hours).
- **FR-013a**: The system MUST include a pair of flights only when its routing appears in DB1B with at least the configured minimum number of sampled passengers over the period (default 30, about 300 actual passengers a year). A routing is the origin, connecting hub and destination of a directional trip with exactly one connection, plus the airline that sold each of its two legs; the two selling airlines must be the same marketing airline or a listed partner pair, matched to the on-time data's marketing airlines through a configured code mapping. Legs whose selling airline is not recorded are not counted, and their share is reported.
- **FR-016**: The system MUST include an itinerary only when its two flights connect on at least the configured recurrence threshold (default 60%) of days in the period. A day connects when an outbound flight is scheduled within the layover limits after that day's scheduled inbound arrival; cancelled flights count as scheduled.
- **FR-017**: The system MUST label partner itineraries as partner connections.
- **FR-018**: The system MUST report each origin/destination pair that has no qualifying itineraries.
- **FR-018a**: For each selected origin/destination pair, the system MUST report how many candidate itineraries each rule excluded: no sold routing (FR-013a), connection-level recurrence (FR-016) and the layover limits (FR-015).

**Connection feasibility (ADR-0005)**

- **FR-019**: For each itinerary and each service date on which both legs were scheduled, the system MUST classify the day as exactly one of: feasible, insufficient time, cancelled or diverted. A day is instead excluded, and counted by reason, when no outbound instance is scheduled within the layover window after that day's inbound flight ("not connecting that day"), or when either leg failed a data-quality check.
- **FR-020**: Raw slack MUST be computed as the outbound leg's actual gate departure minus the inbound leg's actual gate arrival, for the outbound instance matched to that day's inbound flight within the layover window (which may fall on the next calendar day). A day is feasible when raw slack is at least the boarding cutoff (default 15 minutes) plus the minimum connection time.
- **FR-021**: If either leg was cancelled or diverted, the day MUST be classified as a failure of that type, with cancellation taking precedence when both apply.
- **FR-022**: Feasibility MUST be computed only from pairs of legs on the same service date. Per-leg delay distributions MUST NOT be combined as if the legs were independent.
- **FR-023**: For each itinerary, the system MUST report: the number of paired days; the feasibility rate; the count of each failure type; a summary of the raw-slack distribution (at least minimum, 10th, 50th and 90th percentiles); the number of excluded days by reason (FR-019); and the data period.
- **FR-024**: When an itinerary has fewer paired days than the configured minimum sample size (default 30), the system MUST report "insufficient data" and MUST NOT report a feasibility rate.

**Comparison, sensitivity and findings**

- **FR-025**: The analysis MUST cover 10–15 origin/destination pairs through the selected hubs, chosen from the data, not by hand:
  - Only pairs with at least two qualifying itineraries are candidates; the itinerary rules, including FR-013a and FR-016, are applied before ranking.
  - Candidates are ranked by their number of comparable itinerary pairs (FR-026), with ties broken by origin code, then destination code.
  - The highest-ranked candidates are taken, up to the configured count (default 15), subject to: at least half have a regional (non-hub) origin, and no more than a configured number of pairs (default 3) route mainly through any one hub. "Mainly" means the hub used by the largest share of the pair's itineraries.
  - The selection report lists each chosen pair, its rank and its comparable-pair count.
- **FR-026**: Two itineraries are comparable when they share an origin and destination, their total scheduled travel times differ by no more than a configured tolerance (default 60 minutes), and their scheduled departure times from the origin are within a configured window of each other (default 3 hours, compared as local time of day at the origin).
- **FR-027**: The system MUST rerun feasibility under alternative assumptions: minimum connection time of at least 3 values (default 20, 30, 45 minutes), boarding cutoff of at least 3 values (default 10, 15, 20 minutes), and recurrence threshold of at least 3 values (default 50%, 60%, 75%). Hub selection is fixed at the default assumptions and is not rerun per scenario. A scenario's minimum connection time moves every minimum by the same amount: partner and per-hub minimums keep their difference from the default (for example partner connections use 35, 45 and 60 minutes). For each showcase pair the report MUST state the distinct settings of minimum connection time and boarding cutoff at which its order was checked.
- **FR-028**: The system MUST flag a pair of comparable itineraries as assumption-sensitive when their order by feasibility reverses in any sensitivity scenario. A pair in which either itinerary does not qualify under a scenario (for example, below that scenario's recurrence threshold) is reported as missing from that scenario, not treated as a reversal.
- **FR-029**: A showcase example is a pair of comparable itineraries, both with sufficient data, observed on at least the minimum sample size of the same dates (so they were real alternatives at the same time), and not assumption-sensitive, whose feasibility rates differ by at least 10 percentage points (configurable) **and** whose difference is statistically significant: the 95% confidence interval for the difference in feasibility rates MUST exclude zero. The method used MUST either account for both itineraries being observed on the same dates or be conservative (never narrower than such a method), and MUST be documented in the finding.
- **FR-030**: The go criterion is met when at least 3 showcase examples exist, spread across at least 2 different hubs. Otherwise the decision is no-go, or a documented pivot: a proposed change of scope or approach (for example, other hubs, a different measure, or a different product angle), stated with the evidence from this analysis that supports it.
- **FR-031**: The finding MUST be recorded as a new ADR stating the hub selection and its rationale, the go/no-go criteria, whether each was met, the decision, the showcase examples, and the known limitations.
- **FR-032**: Every reported result MUST be described as connection feasibility, not as observed passenger outcomes, and as a historical frequency, not a prediction of future feasibility. The finding MUST list known limitations: airlines holding flights for connecting passengers, gate changes, how full flights were, and assumed rather than measured transfer times. It MUST also state the DB1B period and that DB1B is a 10% ticket sample, and that DB1B fares are not used.

**Reproducibility and verification**

- **FR-033**: Running the full analysis from the pinned configuration with no pre-existing data MUST regenerate every reported number and the hub selection identically.
- **FR-034**: Time conversion, hub selection, itinerary rules, outcome classification, summary statistics and sensitivity logic MUST be covered by automated tests that use small, committed reference samples, including the edge cases listed above.

### Key Entities

- **Flight record**: one scheduled flight instance from the on-time data. Identified by marketing airline, flight number, service date and departure airport; also carries operating airline, arrival airport, scheduled and actual gate times, cancelled/diverted status and delay causes.
- **Passenger traffic record**: monthly passengers boarded per airport and airline, from the passenger traffic data.
- **Sold routing**: an origin, connecting hub, destination and pair of selling airlines, with its number of sampled DB1B passengers in the period.
- **Airport**: an airport code with its time zone and its role in this analysis (selected hub, candidate or regional origin).
- **Hub candidate metrics**: per candidate airport, the airline count, air traffic, passenger volume, weather profile, eligibility, hub score and rank.
- **Hub selection**: the selected hubs, each with the reason for selection, plus any unmet constraints.
- **Partner pair**: two marketing airlines whose flights can be combined into one itinerary.
- **Itinerary**: a recurring pairing of an inbound and an outbound flight number through a hub, with its origin, destination, marketing airline(s), scheduled layover, total scheduled travel time and partner label.
- **Daily connection outcome**: for one itinerary on one service date, the raw slack (if both legs operated) and the classification.
- **Itinerary result**: per itinerary and scenario, the sample size, feasibility rate or "insufficient data", failure counts, slack percentiles and data period.
- **Sensitivity scenario**: one combination of minimum connection time, boarding cutoff and recurrence threshold.
- **Showcase example**: a pair of comparable itineraries meeting the showcase definition.
- **Go/no-go finding**: the decision record with hub rationale, criteria, results, examples and limitations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A full rerun from pinned configuration, starting with no data, reproduces 100% of reported numbers and the same hub selection exactly.
- **SC-002**: 100% of reported feasibility rates show their sample size and data period, and zero rates are reported for itineraries below the minimum sample size.
- **SC-003**: Between 5 and 8 hubs are selected, and the hub selection report gives a documented reason for every selected hub and names every unmet constraint.
- **SC-004**: At least 10 origin/destination pairs are analyzed, at least 5 of them with a regional origin.
- **SC-005**: Sensitivity results cover all 3 assumptions at 3 or more values each, for every analyzed itinerary.
- **SC-006**: Automated checks confirm correct outcomes on a reference sample that includes at least one case each of midnight crossing, time-zone crossing, daylight-saving change, cancellation, diversion, missing actual times and negative slack.
- **SC-007**: A go/no-go decision is recorded, with every criterion explicitly marked met or not met.
- **SC-009**: 100% of analyzed itineraries follow a routing with at least the minimum number of sampled DB1B passengers and connect on at least the recurrence threshold share of days.
- **SC-010**: Every figure the go/no-go decision relies on is produced by the pipeline and reproduced by `verify`; none comes from ad-hoc queries.
- **SC-008**: Excluding data download time, the full analysis completes in under 30 minutes on a reference machine with 4 CPU cores, 16 GB RAM and an SSD. The run records its own runtime, so this is checked from the run's output rather than by hand.

## Out of Scope

- Any user interface, API or deployment
- Fares and price comparisons (DB1B contains fares; they are not used)
- Live or real-time data, and weather forecasts or observations (weather is measured only through delay causes in the historical data)
- International routes and itineraries with two or more stops
- Recovery routing after a missed connection
- Model calibration and chronological holdout testing (Phase 3)
- Final-destination on-time arrival as a separate measure (planned for Phase 1)

## Assumptions

- **Price comparison is replaced by travel-time and departure-time comparison.** Fares are out of scope, so "similar" itineraries are defined by total scheduled travel time and departure time of day (FR-026), not price.
- **Data period:** the latest 12 consecutive months, in whole quarters, for which all three sources are published, configurable: July 2024 to June 2025 when this amendment was written (DB1B is published about 15 months after the quarter ends; on-time and T-100 data sooner). Twelve months are needed to measure seasonal weather patterns, and they increase sample sizes.
- **DB1B:** a 10% sample of tickets from reporting carriers; the passenger minimum applies to sampled passengers. Its ticketing airline corresponds to the on-time data's marketing airline after code mapping.
- **Weather** is measured through the weather-attributed delay cause and weather cancellations recorded in the on-time data. It reflects significant weather that caused delays or cancellations, not weather conditions in general; everyday weather recorded under National Aviation System delays is not counted.
- **Passenger volume** comes from BTS T-100 segment data and counts passengers boarded, including connecting passengers.
- **Major airline networks** for the coverage rule: American, Delta, United, Southwest and Alaska, configurable.
- **Regional origin:** for choosing origin/destination pairs, an airport that is not one of the selected hubs. For hub eligibility (FR-008), an airport outside the candidate pool, because the selected hubs aren't known yet at that point.
- **Transfer time** equals the minimum connection time assumed for the hub; actual walking times are not measured.
- **Partner table:** initially American Airlines and Alaska Airlines; configurable.
- **Minimum sample size:** 30 paired days by default, configurable.
- **Analysis format:** results are presented in an analysis notebook backed by tested, reusable functions, so the same logic can later feed the Phase 1 pipeline.
- **Data source:** BTS on-time performance data includes marketing airline, operating airline, actual gate departure and arrival times, cancellation and diversion status, and delay causes for the period analyzed.
- **Dependencies:** a public time-zone reference for airports (ADR-0008, with the source set by ADR-0011) and the accepted ADRs 0004 (as amended by ADR-0013), 0005, 0008 and 0009.
