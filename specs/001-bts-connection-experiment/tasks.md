---
description: "Task list for the BTS Connection Feasibility Experiment"
---

# Tasks: BTS Connection Feasibility Experiment

**Input**: Design documents from `specs/001-bts-connection-experiment/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: REQUIRED. Constitution Principle II makes calculation, pipeline, time-zone and schema code test-first. In every phase, test tasks come first and must fail before the implementation tasks after them are started.

**Organization**: tasks are grouped by user story. Itinerary rules are foundational because both hub eligibility (US1) and itinerary listing (US2) depend on them.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on unfinished tasks)
- **[Story]**: the user story the task belongs to (US1–US6)

## Path Conventions

- Library: `pipeline/src/flight_pipeline/`
- Tests: `pipeline/tests/` (`unit/`, `integration/`, `fixtures/`)
- Config: `config/phase0.toml`; notebook: `notebooks/`; reports: `reports/phase0/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: project initialization

- [X] T001 Create the uv project in pipeline/pyproject.toml: Python 3.13; package `flight_pipeline` under `src/`; dependencies duckdb, pydantic (v2), numpy, httpx, airportsdata, marimo; dev dependencies pytest, hypothesis, ruff, pyright; console script `flight-pipeline = flight_pipeline.cli:main`; then generate pipeline/uv.lock with `uv sync`
- [X] T002 Create the package skeleton per plan.md: pipeline/src/flight_pipeline/__init__.py, pipeline/src/flight_pipeline/providers/__init__.py, pipeline/src/flight_pipeline/prepare/__init__.py, and empty pipeline/tests/unit/, pipeline/tests/integration/, pipeline/tests/fixtures/ directories (each with a .gitkeep or __init__.py as appropriate)
- [X] T003 [P] Configure ruff (lint + format), pyright (strict for `src/`) and pytest (testpaths, Hypothesis profile with a fixed seed and `deadline=None`) in pipeline/pyproject.toml
- [X] T004 [P] Add `data/derived/` to .gitignore (data/raw/ is already ignored, ADR-0009)
- [X] T005 [P] Create config/phase0.toml with every key and value from contracts/config.md (no omitted defaults)
- [X] T006 [P] Add a GitHub Actions workflow in .github/workflows/pipeline.yml that, on push and pull request, installs uv, runs `uv sync --locked`, then `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright` and `uv run pytest` in `pipeline/`, with no network access needed by tests

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: config, data models, providers, time conversion, normalization and itinerary rules that every user story uses.

**⚠️ CRITICAL**: no user-story work can begin until this phase is complete.

### Reference fixtures

- [X] T007 [P] Create the on-time reference sample pipeline/tests/fixtures/ontime_sample.csv using the exact BTS column names in research.md R1, plus pipeline/tests/fixtures/README.md describing each case. Cover at least: a connection crossing local midnight; a `CRSDepTime` of `2400`; legs crossing time zones; connections on 2025-11-02 and 2026-03-08 (daylight-saving changes); a cancellation with code B; a cancellation with code A; a diversion; an operated flight with missing actual times; negative slack; an identical duplicate row; two conflicting copies of one flight instance; a partner (AA+AS) connection; two legs operated by the same regional airline but sold by different marketing airlines; a flight number below the recurrence threshold; a layover below the minimum and one above 4 hours
- [X] T008 [P] Create pipeline/tests/fixtures/t100_sample.csv (columns per research.md R2) and pipeline/tests/fixtures/expected/ with hand-computed expected values (JSON) for every case in T007, used by later tests

### Configuration and models

- [X] T009 [P] Write failing tests in pipeline/tests/unit/test_config.py: loading config/phase0.toml succeeds; each validation rule in contracts/config.md (ranges, defaults present in sensitivity lists, 12-month periods, season month lists covering each month exactly once, unknown keys rejected) produces a clear error
- [X] T010 Implement Pydantic config models and TOML loading in pipeline/src/flight_pipeline/config.py to pass T009
- [X] T011 [P] Write failing tests in pipeline/tests/unit/test_models.py for model validation rules: data-model.md FlightRecord.sched_arr_utc after FlightRecord.sched_dep_utc and actual times present when FlightRecord.quality_flag is `ok` and not cancelled/diverted; ItineraryResult.feasibility_rate null exactly when ItineraryResult.status is `insufficient_data`; SensitivityScenario.is_default true for exactly one scenario in a set; DailyOutcome.outcome limited to its four values
- [X] T012 Implement all entities from data-model.md as Pydantic models in pipeline/src/flight_pipeline/models.py (FlightRecord, PassengerTraffic, Airport, HubCandidate, HubSelection, FlightPattern, Itinerary, DailyOutcome, ItineraryResult, SensitivityScenario, OdSelection, ComparablePair, Finding), plus a helper that validates a DuckDB/Parquet table against a model, to pass T011

### Providers (Principle VI)

- [X] T013 [P] Define provider interfaces (on-time source, passenger source, time-zone source) in pipeline/src/flight_pipeline/providers/base.py
- [X] T014 [P] Write failing tests in pipeline/tests/unit/test_timezones.py: IATA lookup returns an IANA name for known airports; config overrides take precedence and record their source; missing airports raise an error listing every missing code (FR-004)
- [X] T015 Implement the time-zone provider using airportsdata keyed by IATA (ADR-0011) in pipeline/src/flight_pipeline/providers/timezones.py, populating data-model.md Airport.tz, to pass T014
- [X] T016 [P] Write failing tests in pipeline/tests/unit/test_provider_ontime.py using httpx MockTransport (no network): URL built from the pattern with non-padded month; per-month overrides used; SHA-256 recorded; a pinned checksum mismatch fails; files already present and verified are not downloaded again
- [X] T017 Implement the monthly zip download and extraction in pipeline/src/flight_pipeline/providers/bts_ontime.py to pass T016
- [X] T018 [P] Write failing tests in pipeline/tests/unit/test_provider_t100.py using httpx MockTransport: scripted download success path; on failure, the provider raises an acquisition error carrying manual-download instructions; a manual file is accepted only when its SHA-256 matches config
- [X] T019 Implement the T-100 provider with scripted download and manual-file fallback in pipeline/src/flight_pipeline/providers/bts_t100.py, producing data-model.md PassengerTraffic.year, PassengerTraffic.month, PassengerTraffic.origin, PassengerTraffic.carrier and PassengerTraffic.passengers, to pass T018

### Time conversion and normalization (ADR-0008, research.md R3)

- [X] T020 [P] Write failing tests in pipeline/tests/unit/test_timeconv.py: scheduled departure from `FlightDate` + `CRSDepTime` in the origin zone, including `2400` and `0000`; arrival and actual instants from elapsed and delay minutes; the fixture cases for midnight, time-zone crossing and both daylight-saving dates; plus Hypothesis tests that actual arrival minus actual departure always equals `ActualElapsedTime` and that results never depend on the host machine's time zone
- [X] T021 Implement UTC instant computation in pipeline/src/flight_pipeline/prepare/timeconv.py, producing data-model.md FlightRecord.sched_dep_utc, FlightRecord.sched_arr_utc, FlightRecord.actual_dep_utc and FlightRecord.actual_arr_utc, to pass T020
- [X] T022 [P] Write failing tests in pipeline/tests/unit/test_normalize.py and pipeline/tests/unit/test_quality.py: header validated against the research.md R1 field list (mismatch fails with the differing names); identical duplicates keep one copy and conflicting copies are all excluded; missing actual times flagged; clock-time mismatch share computed against `DepTime`/`ArrTime` and the run fails above `quality.clock_mismatch_max_share`; weather flag derived per FR-007
- [X] T023 Implement raw CSV → typed Parquet normalization in pipeline/src/flight_pipeline/prepare/normalize.py, setting data-model.md FlightRecord.marketing_airline, FlightRecord.operating_airline, FlightRecord.flight_number, FlightRecord.service_date, FlightRecord.cancelled, FlightRecord.diverted, FlightRecord.cancellation_code, FlightRecord.weather_delay_min and FlightRecord.weather_affected, and enforcing the identity uniqueness rule for FlightRecord, to pass the normalize tests in T022
- [X] T024 Implement data-quality checks and quality.json output in pipeline/src/flight_pipeline/prepare/quality.py, setting data-model.md FlightRecord.quality_flag, to pass the quality tests in T022

### Itinerary rules (ADR-0004, research.md R6; shared by US1 and US2)

- [X] T025 [P] Write failing tests in pipeline/tests/unit/test_itineraries.py covering User Story 2 acceptance scenarios 1–5 on the fixtures: recurrence counts cancelled flights as scheduled; pairing by marketing airline or partner pair only, never operating airline; partner minimum of 45 minutes; median layover within limits; deterministic itinerary IDs
- [X] T026 Implement flight patterns and itinerary pairing in pipeline/src/flight_pipeline/itineraries.py, producing data-model.md FlightPattern.scheduled_days, FlightPattern.recurrence, Itinerary.itinerary_id, Itinerary.origin, Itinerary.hub, Itinerary.dest, Itinerary.inbound, Itinerary.outbound, Itinerary.partner_connection, Itinerary.median_layover_min, Itinerary.median_travel_min and Itinerary.median_dep_local_min, for any given set of hub airports, to pass T025

### Command-line interface skeleton

- [X] T027 Implement pipeline/src/flight_pipeline/cli.py with `acquire` and `prepare` commands, `--config`, the exit codes in contracts/cli.md (0, 1, 2), progress on stderr and a one-line summary on stdout
- [X] T028 Validate assumptions against real data: run `acquire` and `prepare` for one month (2026-09); confirm the CSV header matches research.md R1, the clock-mismatch share is below the threshold, and whether `2400` appears; attempt the scripted T-100 download; record findings and any corrections in specs/001-bts-connection-experiment/research.md (R1–R3) and pin the checksums in config/phase0.toml

**Checkpoint**: foundation ready. User-story work can begin.

---

## Phase 3: User Story 1 - Select hubs from the data (Priority: P1) 🎯 MVP

**Goal**: hubs chosen by reproducible rules, with a report explaining each choice.

**Independent Test**: hub selection on a fixed fixture of airport metrics selects exactly the expected hubs, order and reasons.

### Tests for User Story 1

- [X] T029 [P] [US1] Create a hub-metrics fixture pipeline/tests/fixtures/hub_metrics.json with candidates designed to exercise every rule (an airline network covered only below the cut-off, all top hubs peaking in the same season, an ineligible high scorer, a tie in score, missing passenger data, unsatisfiable constraints) and its expected selection
- [X] T030 [P] [US1] Write failing tests in pipeline/tests/unit/test_hub_metrics.py: candidate pool is the top 30 airports by scheduled departures, with ties at the cut-off broken by airport code (FR-006); airline count at the 5% share; weather share overall and by season, peak season, and `unknown` for a season with no weather-affected departures; missing passengers treated as zero and reported; eligibility counting only itineraries whose origin is outside the pool
- [X] T031 [P] [US1] Write failing tests in pipeline/tests/unit/test_hub_selection.py covering User Story 1 acceptance scenarios 1–5 against the T029 fixture: score scaling and weights, rank tie-break by airport code, airline-coverage and weather swaps in the documented order, unmet constraints reported

### Implementation for User Story 1

- [X] T032 [US1] Implement candidate pool selection and candidate metrics in pipeline/src/flight_pipeline/hubs.py, producing data-model.md HubCandidate.airport, HubCandidate.departures, HubCandidate.airline_count, HubCandidate.airlines, HubCandidate.passengers, HubCandidate.weather_share, HubCandidate.weather_share_by_season, HubCandidate.weather_peak_season, HubCandidate.eligible_itineraries and HubCandidate.eligible (using itineraries.py from T026), and assigning data-model.md Airport.role, to pass T030
- [X] T033 [US1] Implement scoring and constrained selection in pipeline/src/flight_pipeline/hubs.py, producing data-model.md HubCandidate.score, HubCandidate.rank, HubSelection.airport, HubSelection.selected and HubSelection.reason, plus the list of unmet constraints later stored in data-model.md Finding.unmet_constraints, following the selection procedure in data-model.md, to pass T031
- [X] T034 [US1] Add the `select-hubs` command to pipeline/src/flight_pipeline/cli.py, writing hub_candidates.parquet and hub_selection.parquet with the sort orders in contracts/outputs.md
- [X] T035 [US1] Implement the hub-selection section of the report (every candidate's metrics, score, eligibility, rank; selected hubs with reasons; unmet constraints) in pipeline/src/flight_pipeline/report.py, with a test in pipeline/tests/unit/test_report.py

**Checkpoint**: hub selection works and is reported on its own.

---

## Phase 4: User Story 2 - Identify plausible one-stop itineraries (Priority: P1)

**Goal**: itineraries through the selected hubs, and 10–15 origin/destination pairs chosen from the data.

**Independent Test**: itinerary construction and pair selection on the fixtures match the hand-checked expected lists exactly.

### Tests for User Story 2

- [X] T036 [P] [US2] Write failing tests in pipeline/tests/unit/test_comparability.py: two itineraries are comparable only with the same origin and destination, travel times within 60 minutes and departures within 3 hours of local time of day (FR-026), including departures on either side of local midnight
- [X] T037 [P] [US2] Write failing tests in pipeline/tests/unit/test_od_selection.py: only pairs with at least two qualifying itineraries; ranking by comparable-pair count with ties by origin then destination; at least half regional origins; at most 3 pairs per main hub; pairs with no qualifying itineraries reported (FR-018)

### Implementation for User Story 2

- [X] T038 [US2] Implement the comparability rule in pipeline/src/flight_pipeline/compare.py, using data-model.md Itinerary.median_travel_min and Itinerary.median_dep_local_min and producing ComparablePair.travel_diff_min and ComparablePair.dep_diff_min, to pass T036
- [X] T039 [US2] Implement origin/destination ranking and selection in pipeline/src/flight_pipeline/od_selection.py, producing data-model.md OdSelection.comparable_pairs, OdSelection.main_hub, OdSelection.regional_origin, OdSelection.rank and OdSelection.selected, to pass T037
- [X] T040 [US2] Add the `build` command to pipeline/src/flight_pipeline/cli.py, writing itineraries.parquet and od_selection.parquet with the sort orders in contracts/outputs.md
- [X] T041 [US2] Add the itinerary and pair-selection sections to pipeline/src/flight_pipeline/report.py (selected pairs with rank and comparable-pair count; pairs without qualifying itineraries), with tests in pipeline/tests/unit/test_report.py

**Checkpoint**: US1 and US2 together produce the analyzed routes.

---

## Phase 5: User Story 3 - Measure connection feasibility with honest sample sizes (Priority: P1)

**Goal**: per-itinerary feasibility with failure breakdown, slack percentiles, sample size and data period.

**Independent Test**: daily outcomes and summary figures on the fixtures match hand-computed expected values, including midnight, time-zone and daylight-saving cases.

### Tests for User Story 3

- [X] T042 [P] [US3] Write failing tests in pipeline/tests/unit/test_daily_outcomes.py covering User Story 3 acceptance scenarios 1–4 and 6: outbound instance matched within the layover window after that day's inbound arrival, including next-day departures; outcome precedence cancelled → diverted → feasible / insufficient time; negative slack is insufficient time; days with no matching outbound and days with failed quality checks excluded and counted separately
- [X] T043 [P] [US3] Write failing tests in pipeline/tests/unit/test_itinerary_results.py covering User Story 3 acceptance scenario 5: rates, failure counts and slack percentiles (min, p10, p50, p90) against expected values; "insufficient data" with no rate below 30 paired days; data period present on every row

### Implementation for User Story 3

- [X] T044 [US3] Implement daily matching and classification in pipeline/src/flight_pipeline/feasibility.py, producing data-model.md DailyOutcome.raw_slack_min and DailyOutcome.outcome per its state rule, to pass T042
- [X] T045 [US3] Implement per-itinerary results in pipeline/src/flight_pipeline/feasibility.py, producing data-model.md ItineraryResult.itinerary_id, ItineraryResult.scenario_id, ItineraryResult.paired_days, ItineraryResult.excluded_not_connecting, ItineraryResult.excluded_quality, ItineraryResult.feasibility_rate, ItineraryResult.status, ItineraryResult.count_feasible, ItineraryResult.count_insufficient_time, ItineraryResult.count_cancelled, ItineraryResult.count_diverted, ItineraryResult.slack_min, ItineraryResult.slack_p10, ItineraryResult.slack_p50, ItineraryResult.slack_p90, ItineraryResult.period_start and ItineraryResult.period_end, computing rates from integer counts per research.md R8, to pass T043
- [X] T046 [US3] Add the `analyze` command (default scenario) to pipeline/src/flight_pipeline/cli.py, writing daily_outcomes.parquet and itinerary_results.parquet with the sort orders in contracts/outputs.md
- [X] T047 [US3] Add the results section to pipeline/src/flight_pipeline/report.py following the reporting rules in contracts/outputs.md (sample size and period with every rate, "insufficient data", feasibility wording), with tests in pipeline/tests/unit/test_report.py that fail on any passenger-outcome wording

**Checkpoint**: the core measurement works end to end on one scenario.

---

## Phase 6: User Story 4 - Test sensitivity to assumptions (Priority: P2)

**Goal**: results under all 27 assumption combinations, with order reversals flagged.

**Independent Test**: scenario results on the fixtures match expected values, and pairs whose order reverses are flagged.

### Tests for User Story 4

- [X] T048 [P] [US4] Write failing tests in pipeline/tests/unit/test_sensitivity.py: 27 scenarios generated from config with deterministic IDs and exactly one default; itineraries rebuilt per recurrence threshold for the selected pairs while hub and pair selection stay fixed (FR-027); a pair whose order reverses in any scenario is flagged (FR-028); pairs missing from a scenario are reported, not treated as reversals

### Implementation for User Story 4

- [X] T049 [US4] Implement scenario generation and per-scenario evaluation in pipeline/src/flight_pipeline/sensitivity.py, producing data-model.md SensitivityScenario.scenario_id, SensitivityScenario.min_connection_min, SensitivityScenario.boarding_cutoff_min, SensitivityScenario.recurrence_threshold and SensitivityScenario.is_default, and ItineraryResult rows for every scenario, to pass the scenario tests in T048
- [X] T050 [US4] Implement order-reversal flagging in pipeline/src/flight_pipeline/sensitivity.py, setting data-model.md ComparablePair.assumption_sensitive, to pass the flagging tests in T048
- [X] T051 [US4] Extend the `analyze` command in pipeline/src/flight_pipeline/cli.py to evaluate all scenarios, and add the sensitivity section to pipeline/src/flight_pipeline/report.py, with tests in pipeline/tests/unit/test_report.py

**Checkpoint**: conclusions can be checked for robustness.

---

## Phase 7: User Story 5 - Record a go/no-go decision with showcase examples (Priority: P2)

**Goal**: showcase examples meeting all conditions, a go/no-go evaluation and the summary report.

**Independent Test**: on the fixtures, the finding states the criteria, which were met, showcase examples that satisfy the definition, and the limitations.

### Tests for User Story 5

- [X] T052 [P] [US5] Write failing tests in pipeline/tests/unit/test_bootstrap.py: the paired day-level bootstrap (research.md R5) recovers a known difference on synthetic data; with independent synthetic itineraries its interval is close to the closed-form interval; a positively correlated pair gives a narrower interval than the independent case; the same seed gives identical intervals
- [X] T053 [P] [US5] Write failing tests in pipeline/tests/unit/test_showcase.py covering User Story 5 acceptance scenarios 1–3: all showcase conditions (sufficient data, comparable, gap ≥ 10 points, interval excluding zero, not assumption-sensitive); a 12-point gap whose interval includes zero is not a showcase; the go criterion (≥ 3 examples across ≥ 2 hubs) met and not met

### Implementation for User Story 5

- [X] T054 [US5] Implement the paired bootstrap in pipeline/src/flight_pipeline/compare.py, ordering each pair per data-model.md ComparablePair.itinerary_a and ComparablePair.itinerary_b, and producing ComparablePair.rate_diff, ComparablePair.ci_low and ComparablePair.ci_high, using the seed and resample count from config, to pass T052
- [X] T055 [US5] Implement showcase selection and the go criterion in pipeline/src/flight_pipeline/compare.py, setting data-model.md ComparablePair.showcase, Finding.criterion_min_examples_met, Finding.criterion_min_hubs_met and Finding.decision (`go` or `no_go` only), and write comparable_pairs.parquet from the `analyze` command, to pass T053
- [X] T056 [US5] Implement the `report` command in pipeline/src/flight_pipeline/report.py and pipeline/src/flight_pipeline/cli.py, writing reports/phase0/summary.json and reports/phase0/summary.md, populating data-model.md Finding.ontime_period_start, Finding.ontime_period_end, Finding.t100_period_start, Finding.t100_period_end, Finding.hubs, Finding.unmet_constraints, Finding.od_pairs, Finding.od_pairs_without_itineraries, Finding.default_results, Finding.showcase_examples, Finding.ci_method, Finding.limitations (the four FR-032 items plus the historical-frequency statement) and Finding.data_quality, with attribution for BTS and airportsdata in summary.md, and tests in pipeline/tests/unit/test_report.py
- [X] T057 [P] [US5] Create the marimo notebook notebooks/phase0_connection_experiment.py that reads only data/derived/phase0/ and reports/phase0/ and shows: hub selection table, feasibility by itinerary with sample sizes, slack distributions for showcase pairs, and the sensitivity summary. Charts use text labels or patterns in addition to color; no calculations beyond formatting. Ship it with a smoke test in pipeline/tests/integration/test_notebook.py that runs the notebook headlessly as a script (`python notebooks/phase0_connection_experiment.py`) against fixture outputs and asserts it exits without errors (Principle II)

**Checkpoint**: the full analysis and finding can be produced from derived tables.

---

## Phase 8: User Story 6 - Reproduce the analysis from scratch (Priority: P3)

**Goal**: one command rebuilds everything identically.

**Independent Test**: delete derived data, rerun from config, and confirm identical results.

### Tests for User Story 6

- [X] T058 [P] [US6] Write a failing end-to-end test in pipeline/tests/integration/test_pipeline_fixtures.py that runs all stages after `acquire` on fixture data and checks the outputs against expected results. (Implementation note: the 10-day reference sample cannot drive a 12-month pipeline, so the end-to-end test generates a deterministic synthetic year in BTS format, pipeline/tests/integration/synthetic.py, whose expected hubs, results and showcases follow from its design; the hand-computed values in pipeline/tests/fixtures/expected/ are checked by the unit tests.)
- [X] T059 [P] [US6] Write a failing determinism test in pipeline/tests/integration/test_determinism.py that runs the fixture pipeline twice into separate directories and asserts identical output-table hashes and identical summary.json; also test that the `verify` command (contracts/cli.md) exits 0 on an unchanged fixture run and exits 1 listing the difference when one output is altered

### Implementation for User Story 6

- [X] T060 [US6] Implement the `run` command in pipeline/src/flight_pipeline/cli.py chaining all stages, skipping downloads already present and verified, and timing the run excluding downloads; and the `verify` command per contracts/cli.md, to pass T058 and the `verify` tests in T059
- [X] T061 [US6] Implement reports/phase0/manifest.json in pipeline/src/flight_pipeline/report.py (fields per contracts/outputs.md, with the run-specific fields `run_at`, `runtime_min`, `runtime_exceeded` and machine description excluded from hashing; a warning on stderr when the runtime exceeds `runtime.limit_min`), and enforce the explicit sort orders from contracts/outputs.md, float rounding and fixed Parquet writer settings (research.md R8) on every written table, to pass T059

**Checkpoint**: all user stories complete and verified on fixtures.

---

## Phase 9: Polish & Cross-Cutting Concerns

- [X] T062 Run the full analysis on real data per quickstart.md; the run passes SC-008 when reports/phase0/manifest.json shows `runtime_exceeded: false`. Then commit reports/phase0/
- [X] T063 Run `uv run flight-pipeline verify` on real data (quickstart.md); SC-001 passes when it exits 0
- [X] T064 [P] Write the first version of docs/methodology.md: data sources and periods, UTC computation (research.md R3), itinerary rules, outcome definition, sample-size rule, hub and pair selection, sensitivity analysis, the paired bootstrap, and the limitations from FR-032
- [X] T065 [P] Create the repository README.md: project purpose, current phase, how to run the Phase 0 pipeline (link to quickstart.md), link to the roadmap, ADRs and methodology, and data attributions
- [X] T066 Write docs/adr/0012-phase0-go-no-go.md from reports/phase0/summary.md (hub selection and rationale, criteria met/not met, decision, showcase examples, limitations) and add it to docs/adr/README.md
- [X] T067 Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright` and `uv run pytest` in pipeline/ and fix any failures
- [X] T068 Run the independent review: a new `feature-reviewer` agent given only `specs/001-bts-connection-experiment` and base branch `main`; save its report as specs/001-bts-connection-experiment/review.md; fix BLOCKING findings, answer SHOULD-FIX findings in review.md, and repeat with a new reviewer until the verdict is APPROVE (constitution, Development Workflow)

---

## Phase 10: Amendment 1, sold routings and connection-level recurrence (ADR-0013; research R10–R12)

**Purpose**: make realism part of the itinerary rules, measured and reproducible. Tests are written first. Afterwards, T062, T063, T066 and T068 are rerun for the amended feature (T083).

### Tests and fixtures

- [X] T069 [P] Create pipeline/tests/fixtures/db1b_sample.csv using the real DB1B Market header (research R10), with: 2-coupon routings for the reference itineraries (CMH:ORD:SAN with AA:AA above the minimum; CMH:ORD:SEA with AA:AS; CMH:ORD:DEN with AA:AA below the minimum); legs with `--`; 1-coupon and 3-coupon rows that must be ignored; one routing spread over two quarters. Document the cases in pipeline/tests/fixtures/README.md, with hand-computed expected values in pipeline/tests/fixtures/expected/sold_routings.json
- [X] T070 [P] Add to pipeline/tests/fixtures/make_ontime_sample.py a pair of flights that each run every day but connect on 5 of 10 days (UA7000 CMH→ORD plus UA7001 ORD→DEN, whose departure alternates between a 60-minute layover and one outside the window), and regenerate ontime_sample.csv
- [X] T071 [P] Write failing tests in pipeline/tests/unit/test_config.py for the single quarter-aligned `[period]`, `[sources.db1b]`, and `min_sold_passengers` and `carrier_map` (contracts/config.md)
- [X] T072 [P] Write failing tests in pipeline/tests/unit/test_provider_db1b.py, using httpx MockTransport: URL per quarter, checksum pinned and recorded, files already present and verified are not downloaded again
- [X] T073 [P] Write failing tests in pipeline/tests/unit/test_db1b.py: aggregation into data-model.md SoldRouting.origin, SoldRouting.hub, SoldRouting.dest, SoldRouting.airline_in, SoldRouting.airline_out and SoldRouting.passengers, matching expected/sold_routings.json; legs with `--` excluded and their share reported; carrier_map applied; extracted CSV deleted afterwards
- [X] T074 [P] Write failing tests in pipeline/tests/unit/test_itineraries.py for User Story 2 scenarios 1, 5 and 6 as amended: a routing below the sold minimum is excluded; partner routings matched on AA:AS; connection-level recurrence excludes the UA7000+UA7001 pair (50% < 60%); data-model.md Itinerary.connect_share and Itinerary.sold_passengers are set; data-model.md OdExclusions counts follow the rule order
- [X] T075 [P] Write failing tests in pipeline/tests/unit/test_sensitivity.py and pipeline/tests/unit/test_report.py: recurrence scenarios apply to connection share; data-model.md ComparablePair.settings_compared counts distinct (minimum connection time, cutoff) settings; the report shows settings compared, exclusion counts per pair, the DB1B period and the sample note

### Implementation

- [X] T076 Implement the single quarter-aligned period and the new configuration keys in pipeline/src/flight_pipeline/config.py; update config/phase0.toml to the period 2024-07 to 2025-06 and clear the outdated on-time and T-100 checksums, to pass T071
- [X] T077 Implement pipeline/src/flight_pipeline/providers/bts_db1b.py, to pass T072
- [X] T078 Implement pipeline/src/flight_pipeline/prepare/db1b.py (extract, aggregate, delete, report unknown-airline share) and wire it into `prepare`, writing sold_routings.parquet, to pass T073
- [X] T079 Implement the R12 rule order in pipeline/src/flight_pipeline/itineraries.py (sold-routing join, connection-level recurrence from daily schedule matching, exclusion counts), use it for hub eligibility and pair selection in pipeline/src/flight_pipeline/stages.py, and write od_exclusions.parquet, to pass T074
- [X] T080 Implement settings_compared and the new report content in pipeline/src/flight_pipeline/sensitivity.py, stages.py and report.py, and add the new Finding fields from data-model.md, to pass T075
- [X] T081 Update the synthetic year (pipeline/tests/integration/synthetic.py) with a matching DB1B sample, so the end-to-end, determinism and notebook tests cover the new rules; update the notebook to show sold passengers and settings compared
- [X] T082 Update docs/methodology.md (sold routings, connection-level recurrence, rule order, settings-based robustness, DB1B limitations) and the README
- [X] T083 Download the new period (`acquire`) and pin all on-time, T-100 and DB1B checksums in config/phase0.toml; then run T062 and T063 again, rewrite ADR-0012 from the new results (T066), and run a new independent review (T068)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: depends on Setup; blocks all user stories. T028 (real-data check) should finish before user-story work, since it may correct research assumptions.
- **US1 (Phase 3)**: depends on Foundational (uses itinerary rules from T026).
- **US2 (Phase 4)**: depends on US1 (pairs are built through selected hubs).
- **US3 (Phase 5)**: depends on US2 (outcomes are computed for selected pairs).
- **US4 (Phase 6)**: depends on US3.
- **US5 (Phase 7)**: depends on US3 for results and US4 for the assumption-sensitivity flag.
- **US6 (Phase 8)**: depends on all stages existing (US1–US5).
- **Polish (Phase 9)**: depends on all user stories.

### User Story Dependencies

The stories form a pipeline, so they are sequential: US1 → US2 → US3 → US4 → US5 → US6. Each story is still independently testable on fixtures, because its tests use committed fixture data rather than the previous stage's real output.

### Within Each User Story

- Tests are written first and must fail before implementation starts.
- Library modules before CLI commands; CLI commands before report sections.
- Finish a story's checkpoint before moving on.

### Parallel Opportunities

- Setup: T003–T006 in parallel after T001–T002.
- Foundational: fixtures (T007, T008) and all test-writing tasks marked [P] (T009, T011, T014, T016, T018, T020, T022, T025) can be written in parallel; T013 in parallel with them.
- Each story: its [P] test tasks run in parallel (for example T029–T031; T036–T037; T042–T043; T052–T053; T058–T059).
- T057 (notebook) in parallel with T054–T056 once output tables exist.
- Polish: T064 and T065 in parallel.

---

## Parallel Example: User Story 1

```bash
# Write the US1 fixture and tests together:
Task: "T029 Create hub-metrics fixture in pipeline/tests/fixtures/hub_metrics.json"
Task: "T030 Write failing tests in pipeline/tests/unit/test_hub_metrics.py"
Task: "T031 Write failing tests in pipeline/tests/unit/test_hub_selection.py"

# Then implement in order:
Task: "T032 Candidate metrics in pipeline/src/flight_pipeline/hubs.py"
Task: "T033 Scoring and constrained selection in pipeline/src/flight_pipeline/hubs.py"
```

---

## Implementation Strategy

### MVP first

1. Complete Phase 1 (Setup) and Phase 2 (Foundational), including the real-data check T028.
2. Complete Phase 3 (US1). **Stop and review:** does the hub selection look sensible on real data?
3. Continue with US2 and US3. This is the first point where the core question (do comparable itineraries differ?) gets an answer.

### Incremental delivery

- After each story's checkpoint, the owner reviews that phase's code and tests before the next one starts (constitution).
- US4 and US5 turn the measurement into a defensible decision; US6 makes it reproducible.
- Phase 9 produces the deliverables: methodology, README, the go/no-go ADR and the independent review.

---

## Notes

- [P] tasks touch different files and have no dependency on unfinished tasks.
- Commit after each task or small group of tasks; commit spec files with the code they describe.
- Tests never use the network (constitution Principle II).
- Field constraints are defined in data-model.md; tasks cite `Entity.field` rather than restating them.
