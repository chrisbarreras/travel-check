---
description: "Task list for the showcase data pipeline"
---

# Tasks: Showcase Data Pipeline

**Input**: Design documents from `specs/002-showcase-data-pipeline/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: required. The constitution (Principle II) makes calculation, pipeline, time-zone and schema code test-first: each test task is written and fails before its implementation task.

**Organization**: by user story (spec.md). All paths are from the repository root; pipeline code is under `pipeline/`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: the user story (US1–US6) the task serves

---

## Phase 1: Setup

**Purpose**: freeze Phase 0, add the Phase 1 configuration and the shared contract folders.

- [X] T001 Tag the commit that produced `reports/phase0/` as `phase0-final` (research R15), and record the tag in the evidence line of docs/adr/0012-phase0-go-no-go.md and in README.md
- [X] T002 Write docs/adr/0014-schedule-slot-itinerary-identity.md (itineraries identified by schedule slot, research R1; layover limits applied only through daily matching with a lossless bound pre-filter, research R2), mark ADR-0004's identity and median-layover rules and the related parts of ADR-0013 as superseded by ADR-0014, and add it to docs/adr/README.md (constitution: changing an ADR's decision requires a superseding ADR)
- [X] T003 [P] Create config/phase1.toml from config/phase0.toml with the new keys of contracts/config.md (`[itineraries] identity`, `slot_window_min`; `[showcase]`; `[insights]`; `[notes]`), without the removed median-layover rule
- [X] T004 [P] Create config/disruption_notes.toml with the July 2024 CrowdStrike outage and other events in July 2024 – June 2025 that affected a showcase airline or hub and are documented by an official source (DOT, FAA or NWS), each with that `https` source (research R12)
- [X] T005 [P] Create shared/schemas/, shared/types/ and shared/test-cases/ with a README.md each stating that the files are generated or shared and never edited by hand; add `site-data/` and `shared/` to .gitattributes LF rules
- [X] T006 [P] Extend .github/workflows/pipeline.yml with Node.js 20 setup and a `uv run flight-pipeline schemas --check` step (research R6)

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: configuration and published-shape models that every story uses, and the fixtures the tests need.

**⚠️ No user-story work starts before this phase is complete.**

- [X] T007 Write failing tests in pipeline/tests/unit/test_config_phase1.py for the contracts/config.md rules: required new keys, unknown keys rejected, `slot_window_min` 10–90, share and margin ranges, `routes_min` ≤ `routes_max`, disruption notes needing a date range inside the period, an airline or airport, text and an `https` source
- [X] T008 Implement the Phase 1 configuration models and the disruption-note loader in pipeline/src/flight_pipeline/config.py to pass T007
- [X] T009 [P] Write failing tests in pipeline/tests/unit/test_showcase_models.py for the published shapes in data-model.md: data-model.md `ShowcaseIndex.schema_version` a semantic version and data-model.md `ShowcaseIndex.attribution` listing BTS, airportsdata and tzdata; data-model.md `Rate.rate` null exactly when data-model.md `Rate.status` is `insufficient_data`, and data-model.md `Rate.paired_days` at least the minimum when `ok`; data-model.md `Alternative.ci_low` at least −margin and data-model.md `Alternative.minutes_saved` at least the minimum saving; data-model.md `MonthRate.status` one of `ok`, `insufficient_data`, `no_flights`; data-model.md `DailySeries.outcome` codes `F`, `T`, `C`, `D` with data-model.md `DailySeries.slack_min` null exactly for `C` and `D`; data-model.md `Coverage.not_covered` kinds
- [X] T010 Implement the published models in pipeline/src/flight_pipeline/showcase/models.py to pass T009 (ShowcaseIndex, Coverage, RouteSummary, RouteFile, ShowcaseItinerary, Rate, ShowcaseComparison, Alternative, ConnectingOption, DisruptionNote, ShowcaseManifest and their parts), enforcing data-model.md `Rate.status`, data-model.md `Rate.rate` and data-model.md `Rate.paired_days`; data-model.md `Alternative.ci_low` and data-model.md `Alternative.minutes_saved`; data-model.md `MonthRate.status` and data-model.md `MonthRate.rate`; data-model.md `DailySeries.outcome`; data-model.md `Coverage.not_covered`; data-model.md `ShowcaseIndex.schema_version` (semantic version); and data-model.md `ShowcaseIndex.attribution`
- [X] T011 [P] Extend pipeline/tests/fixtures/make_ontime_sample.py and regenerate ontime_sample.csv with: an airline flying the same two schedules daily under changing flight numbers (WN, new numbers on alternate days); two schedules of one airline and route on the same day within one window; a leg whose schedule shifts for the rest of the period (schedule change); an itinerary whose outbound on the last day falls after the loaded data; a nonstop on a fixture route; document each case in pipeline/tests/fixtures/README.md with hand-computed results in pipeline/tests/fixtures/expected/slots.json
- [X] T012 [P] Extend pipeline/tests/integration/synthetic.py with a renumbering airline, nonstop flights on some routes, and enough routes and hubs for curation (at least 8 eligible routes, one dominant market), keeping the design-derived expectations in its docstring

**Checkpoint**: configuration, published models and fixtures exist; stories can start.

---

## Phase 3: User Story 1 - Itineraries that reflect how airlines actually fly (Priority: P1) 🎯 MVP

**Goal**: schedule-slot identity, layover limits through daily matching only, nonstop comparison, per-airline coverage, regional origins outside the pool.

**Independent Test**: on the fixtures, the renumbering airline forms one itinerary; the schedule-change itinerary qualifies with its layover from connecting days; every itinerary has a nonstop comparison; on the synthetic year every airline has itineraries.

### Tests for User Story 1 ⚠️ (write first, must fail)

- [X] T013 [P] [US1] Write failing tests in pipeline/tests/unit/test_slots.py: gap clustering within `slot_window_min` (research R1); a cluster wider than twice the window split at its largest gap; two same-day flights in one cluster kept apart; deterministic `slot_id`; data-model.md `ScheduleSlot.ref_dep_local_min` (0–1439, median), data-model.md `ScheduleSlot.min_dep_local_min` and data-model.md `ScheduleSlot.max_dep_local_min`, data-model.md `ScheduleSlot.recurrence`, data-model.md `ScheduleSlot.flight_numbers` shares; data-model.md `SlotDay` identity unique
- [X] T014 [P] [US1] Write failing tests in pipeline/tests/unit/test_itineraries.py (replacing the pattern-based cases): itineraries as slot pairs; the bound pre-filter never drops a candidate that connects (Hypothesis property over random schedules) and drops one that cannot; layover limits applied only per day; the schedule-change fixture qualifies (round-7 case); end-of-period days excluded from both counts, setting data-model.md `Itinerary.eligible_days` and data-model.md `Itinerary.connect_share`; data-model.md `Itinerary.median_layover_min` and data-model.md `Itinerary.median_travel_min` from connecting days, and data-model.md `Itinerary.median_dep_local_min` equal to the inbound slot's reference time; exclusion counts with `excluded_bounds` and `excluded_not_connecting`
- [X] T015 [P] [US1] Write failing tests in pipeline/tests/unit/test_nonstop.py: nonstop median per pair (research R3), data-model.md `Itinerary.nonstop_median_min` null when there is no nonstop, data-model.md `Itinerary.nonstop_ratio` rounded to 0.1
- [X] T016 [P] [US1] Write failing tests in pipeline/tests/unit/test_coverage.py: itineraries and sold passengers per marketing airline; each major network without itineraries named with a reason (FR-005); regional origin = outside the candidate pool (FR-006)

### Implementation for User Story 1

- [X] T017 [US1] Implement schedule slots and slot days in pipeline/src/flight_pipeline/slots.py to pass T013, producing data-model.md `ScheduleSlot.ref_dep_local_min`, data-model.md `ScheduleSlot.min_dep_local_min`, data-model.md `ScheduleSlot.max_dep_local_min`, data-model.md `ScheduleSlot.recurrence`, data-model.md `ScheduleSlot.flight_numbers` and the unique data-model.md `SlotDay` identity
- [X] T018 [US1] Rework pipeline/src/flight_pipeline/itineraries.py to build itineraries from slot pairs with the research R2 rule order (recurrence, bound pre-filter, sold routing, daily matching), end-of-period exclusion and daily medians, to pass T014, producing data-model.md `Itinerary.connect_share`, data-model.md `Itinerary.eligible_days`, data-model.md `Itinerary.median_layover_min`, data-model.md `Itinerary.median_travel_min` and data-model.md `Itinerary.median_dep_local_min` (0–1439, the inbound slot's reference); adapt pipeline/src/flight_pipeline/feasibility.py daily matching to slots
- [X] T019 [P] [US1] Implement pipeline/src/flight_pipeline/nonstop.py to pass T015, producing data-model.md `Itinerary.nonstop_median_min` and data-model.md `Itinerary.nonstop_ratio`
- [X] T020 [US1] Implement per-airline coverage and the outside-the-pool regional origin in pipeline/src/flight_pipeline/hubs.py and pipeline/src/flight_pipeline/od_selection.py to pass T016
- [X] T021 [US1] Wire slots, the new itinerary rules and nonstop medians into select-hubs, build and analyze in pipeline/src/flight_pipeline/stages.py and pipeline/src/flight_pipeline/cli.py, writing to `data/derived/phase1/`; update pipeline/tests/unit and integration tests that relied on flight-number identity

**Checkpoint**: US1 works on fixtures and the synthetic year.

---

## Phase 4: User Story 2 - A curated, balanced showcase (Priority: P1)

**Goal**: 8–12 routes chosen by the research R4 rules, caps enforced, landing example with reason.

**Independent Test**: on the synthetic year, the dominant market is capped at one third, at least half the comparisons are cross-hub where possible, and the landing example meets its rule.

- [X] T022 [P] [US2] Write failing tests in pipeline/tests/unit/test_curation.py: candidate rule, greedy order and tie-breaks, route/airline/hub caps (data-model.md `RouteSummary.share_of_showcase` never above `max_share_route`), regional share with shortfall reporting, at least half of showcase comparisons cross-hub with swaps and shortfall reporting (research R4 step 5, SC-002), minimum route count shortfall, landing example rule (cross-hub, lower not tight, compared at every setting) with its reason, determinism
- [X] T023 [US2] Implement pipeline/src/flight_pipeline/curation.py to pass T022
- [X] T024 [US2] Add the `curate` stage and command in pipeline/src/flight_pipeline/stages.py and pipeline/src/flight_pipeline/cli.py (contracts/cli.md), writing `data/derived/phase1/showcase_routes.parquet`, and add `curate` to `run`

**Checkpoint**: US1 and US2 produce a curated set.

---

## Phase 5: User Story 3 - Data the explorer can trust and use directly (Priority: P1)

**Goal**: validated, stable, size-budgeted JSON with coverage, plus generated JSON Schema and TypeScript types checked in CI.

**Independent Test**: publish on the synthetic year; every file validates; bytes are stable; a stale type file makes `schemas --check` fail.

- [X] T025 [P] [US3] Write failing tests in pipeline/tests/unit/test_publish.py: stable bytes (sorted keys, compact, LF, 6-decimal floats), validation failure stops the run, both size budgets on gzip bytes (2 MB total; 150 KB for `index.json` plus `landing.json`, the SC-007 load-time proxy) with per-file report, `landing.json` self-contained, data-model.md `ShowcaseIndex.coverage` present with every `not_covered` kind (FR-015a), data-model.md `ShowcaseIndex.definitions` covering every measure used, and a forbidden-wording scan over every published text field (FR-014; also the Phase 0 follow-up to scan whole outputs)
- [X] T026 [P] [US3] Write failing tests in pipeline/tests/unit/test_schemas.py: the exported JSON Schema covers every published model; `schemas --check` exits 1 when shared/schemas or shared/types differ from a fresh generation and 0 when they match (generator call stubbed in unit tests; one integration test runs the real pinned generator when Node is available)
- [X] T027 [US3] Implement pipeline/src/flight_pipeline/showcase/publish.py (index, landing, route files, both size budgets, coverage, definitions, attribution) to pass T025, writing data-model.md `ShowcaseIndex.coverage` with data-model.md `Coverage.not_covered`, data-model.md `ShowcaseIndex.definitions`, data-model.md `ShowcaseIndex.attribution` and data-model.md `ShowcaseIndex.schema_version`
- [X] T028 [US3] Implement pipeline/src/flight_pipeline/schemas.py (JSON Schema export; TypeScript generation with the pinned `json-schema-to-typescript` through `npx`; `--check`) to pass T026
- [X] T029 [US3] Add the `publish` and `schemas` commands to pipeline/src/flight_pipeline/cli.py and `publish` to `run` (contracts/cli.md)

**Checkpoint**: the P1 stories deliver a usable, checked data contract (MVP).

---

## Phase 6: User Story 4 - What-if transfer time in the browser (Priority: P2)

**Goal**: per-day slack and outcomes per curated itinerary, reproducing the pipeline's rate exactly; shared test cases for both languages.

**Independent Test**: recomputing from the stored daily values at the default assumptions equals the published rate for every curated itinerary.

- [X] T030 [P] [US4] Write shared/test-cases/slack-feasibility.json (research R7): hand-computed cases including boundary slack, negative slack, cancelled and diverted days, empty series and below-minimum samples
- [X] T031 [P] [US4] Write failing tests in pipeline/tests/unit/test_slack_cases.py that run every shared case against the pipeline's feasibility calculation, and in pipeline/tests/integration/test_showcase_slider.py that recompute every curated itinerary's rate from data-model.md `ShowcaseItinerary.daily` and compare it with data-model.md `ShowcaseItinerary.result` (SC-004)
- [X] T032 [US4] Write the columnar daily series (data-model.md `DailySeries.day_offset`, data-model.md `DailySeries.slack_min`, data-model.md `DailySeries.outcome`) and data-model.md `ShowcaseItinerary.excluded_days` in pipeline/src/flight_pipeline/showcase/publish.py, and the default assumptions in data-model.md `ShowcaseIndex.assumptions`, to pass T031

---

## Phase 7: User Story 5 - Traveler insights for each itinerary (Priority: P2)

**Goal**: faster alternatives, connecting options, buffer, failure types, monthly view with notes, schedule warnings and find parameters.

**Independent Test**: each insight matches hand-computed fixture values, including the "none applies" cases.

### Tests for User Story 5 ⚠️ (write first, must fail)

- [X] T033 [P] [US5] Write failing tests in pipeline/tests/unit/test_alternatives.py: faster alternatives with no travel-time tolerance, the departure window, minimum saving and the equivalence bound on the paired bootstrap (research R8); connecting options sharing the inbound slot, ranked, `better` only when the interval excludes zero (research R9); empty results when none apply
- [X] T034 [P] [US5] Write failing tests in pipeline/tests/unit/test_buffer.py: data-model.md `Buffer.needed_layover_min` as the 95% lower-rule quantile of threshold + layover − slack over operated days, rounded up to 5 minutes; cancelled and diverted days excluded and counted in data-model.md `Buffer.operated_days` (research R10)
- [X] T035 [P] [US5] Write failing tests in pipeline/tests/unit/test_monthly.py: data-model.md `MonthRate.status` and data-model.md `MonthRate.rate` with the 20-day monthly minimum (research R11), `no_flights` months, disruption notes attached by date range and airline or airport, and never used in a calculation (research R12); and, in pipeline/tests/unit/test_failures.py, the failure breakdown (FR-021) with data-model.md `FailureBreakdown.dominant`
- [X] T036 [P] [US5] Write failing tests in pipeline/tests/unit/test_schedule_changes.py: schedule changes of at least 10 minutes lasting at least 7 scheduled days with date, leg and times (research R13); data-model.md `ScheduleWarnings.connect_share`; find parameters with the most frequent flight number per leg and data-model.md `FindParams.legs` shares (research R14)

### Implementation for User Story 5

- [X] T037 [P] [US5] Implement pipeline/src/flight_pipeline/insights/alternatives.py to pass T033, producing data-model.md `Alternative.minutes_saved` and data-model.md `Alternative.ci_low` within their bounds
- [X] T038 [P] [US5] Implement pipeline/src/flight_pipeline/insights/buffer.py to pass T034, producing data-model.md `Buffer.needed_layover_min` and data-model.md `Buffer.operated_days`
- [X] T039 [P] [US5] Implement pipeline/src/flight_pipeline/insights/monthly.py (monthly view, disruption notes and the failure breakdown) to pass T035, producing data-model.md `MonthRate.status`, data-model.md `MonthRate.rate` and data-model.md `FailureBreakdown.dominant`
- [X] T040 [P] [US5] Implement pipeline/src/flight_pipeline/insights/schedule.py to pass T036
- [X] T041 [US5] Add the `insights` stage and command (contracts/cli.md), add it to `run` before `publish`, and write every insight into the route files in pipeline/src/flight_pipeline/showcase/publish.py, including data-model.md `ShowcaseItinerary.tight_layover` and data-model.md `ShowcaseItinerary.sold`

---

## Phase 8: User Story 6 - Reproducible, verifiable showcase data (Priority: P3)

**Goal**: byte-identical reruns and `verify` over every new output, with a manifest that records code identity.

**Independent Test**: two synthetic runs are identical; a one-byte edit in a committed showcase file or a stale type file fails `verify` and is named.

- [X] T042 [P] [US6] Write failing tests in pipeline/tests/integration/test_showcase_determinism.py: two runs give identical site-data/showcase/ and shared/ files; `verify` fails and names the file after a one-byte hand edit in a route file, in index.json and in shared/types/showcase.ts, and after a changed package or config (the Phase 0 follow-up regression test)
- [X] T043 [P] [US6] Write failing tests in pipeline/tests/unit/test_manifest.py: data-model.md `ShowcaseManifest` records sources, config and disruption-notes checksums, package versions, code version (package version and git commit) and output checksums; a carried runtime is kept only when config, sources and code version match (FR-027)
- [X] T044 [US6] Extend `verify` in pipeline/src/flight_pipeline/cli.py to rerun every stage into a temporary directory, extracting DB1B there too (contracts/cli.md; Phase 0 follow-up), and compare every output including site-data/showcase/ and shared/, to pass T042
- [X] T045 [US6] Implement the showcase manifest and the extended carry-over rule in pipeline/src/flight_pipeline/showcase/publish.py and pipeline/src/flight_pipeline/stages.py to pass T043

---

## Phase 9: Polish & cross-cutting

- [X] T046 [P] Update docs/methodology.md: schedule slots, layover by daily matching with the bound pre-filter, end-of-period exclusion, nonstop comparison, curation and caps, every insight's definition and threshold, the monthly minimum, disruption notes, and the published-data contract (FR-028)
- [X] T047 [P] Update README.md (Phase 1 status, how to build the showcase data, the `shared/` contract) and docs/roadmap.md (Phase 1 progress)
- [ ] T048 Run `uv run flight-pipeline run --config ../config/phase1.toml` on the pinned real data; review coverage (SC-001), balance (SC-002), size (SC-007) and runtime; then rerun with DuckDB limited to 4 threads and record that runtime against the 30-minute limit (SC-008); commit site-data/showcase/ and shared/
- [ ] T049 Run `uv run flight-pipeline verify --config ../config/phase1.toml` and `uv run flight-pipeline schemas --check`; both must pass
- [ ] T050 Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright` and `uv run pytest` in pipeline/ and fix any failures
- [ ] T051 Run the quickstart.md validation scenarios and record the results
- [ ] T052 Run the independent review: a new `feature-reviewer` agent given only `specs/002-showcase-data-pipeline` and base branch `main`; save its report as specs/002-showcase-data-pipeline/review.md; fix BLOCKING findings, answer SHOULD-FIX findings in review.md, and repeat with a new reviewer until the verdict is APPROVE (constitution, Development Workflow)

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: none. T001 and T002 come before any change to pipeline behaviour.
- **Foundational (Phase 2)**: after Setup; blocks every story.
- **US1 (Phase 3)**: after Foundational. Every later story builds on its itineraries.
- **US2 (Phase 4)**: after US1 (curates its results).
- **US3 (Phase 5)**: after US2 (publishes the curated set); with US1 and US2 it is the MVP.
- **US4 (Phase 6)** and **US5 (Phase 7)**: after US3; independent of each other.
- **US6 (Phase 8)**: after US3; best after US4 and US5 so `verify` covers their outputs.
- **Polish (Phase 9)**: after all stories.

### Within each story

- Tests first, and they must fail before implementation (Principle II).
- Models before calculations, calculations before stages and commands, stages before publishing.

### Parallel opportunities

- Setup: T003–T006 in parallel after T001 and T002.
- Foundational: T009, T011 and T012 in parallel with T007.
- US1: tests T013–T016 in parallel; T019 in parallel with T017–T018.
- US3: T025 and T026 in parallel.
- US4 and US5 can proceed in parallel; within US5, T033–T036 and then T037–T040 in parallel.
- US6: T042 and T043 in parallel.

---

## Parallel Example: User Story 5

```bash
Task: "T033 Write failing tests in pipeline/tests/unit/test_alternatives.py"
Task: "T034 Write failing tests in pipeline/tests/unit/test_buffer.py"
Task: "T035 Write failing tests in pipeline/tests/unit/test_monthly.py"
Task: "T036 Write failing tests in pipeline/tests/unit/test_schedule_changes.py"
```

---

## Implementation Strategy

### MVP first

1. Setup and Foundational.
2. US1 (identity and rules), then US2 (curation), then US3 (published contract).
3. **Stop and validate**: publish on the synthetic year and on real data; the explorer features can start from this contract.

### Incremental delivery

4. US4 (slider data) and US5 (insights), each validated on fixtures and real data.
5. US6 (reproducibility), then Polish, the real-data run, `verify`, and the independent review.

## Notes

- Tests are deterministic and never use the network; the TypeScript generator runs only in `schemas` and its CI check.
- Phase 0's results are reproduced from the `phase0-final` tag, not by the new code (research R15).
- Commit after each task or logical group, on the feature branch only.
