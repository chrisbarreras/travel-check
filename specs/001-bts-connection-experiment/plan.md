# Implementation Plan: BTS Connection Feasibility Experiment

**Branch**: `001-bts-connection-experiment` | **Date**: 2026-11-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-bts-connection-experiment/spec.md`

## Summary

Determine from 12 months of public BTS data whether comparable one-stop itineraries differ meaningfully in connection feasibility. A reproducible Python pipeline, driven by one pinned configuration file:

1. downloads BTS on-time data (monthly zip files) and T-100 passenger data, and loads airport time zones;
2. normalizes every flight to UTC instants, computed from scheduled times plus BTS delay and elapsed-time minutes so that date roll-over is never inferred from clock times;
3. selects hubs from the data using score, airline-coverage and weather-diversity rules;
4. builds recurring itineraries at the schedule level, then classifies daily outcomes only for selected origin/destination pairs;
5. computes feasibility, slack percentiles, sensitivity scenarios and showcase pairs, using a paired day-level bootstrap for confidence intervals;
6. writes result tables and a summary report.

A marimo notebook presents the results, and the go/no-go finding is recorded as a new ADR. All calculation logic is in tested library modules; the notebook only reads outputs and draws charts.

## Technical Context

**Language/Version**: Python 3.13, managed with uv (ADR-0002)

**Primary Dependencies**: DuckDB (analytical queries over Parquet), Pydantic v2 (config and output models, ADR-0007), NumPy (bootstrap), httpx (downloads), airportsdata (airport time zones, see research R4 and ADR-0011), tzdata (time-zone rules, pinned so results don't depend on the host OS), marimo and altair (notebook and its charts). Exact versions are locked in `pipeline/uv.lock`.

**Storage**: Parquet files queried with DuckDB (ADR-0003). Raw downloads in `data/raw/` and derived tables in `data/derived/`, both ignored by git (ADR-0009). Small summary outputs committed in `reports/phase0/`.

**Testing**: pytest, Hypothesis (randomized tests for time conversion and slack), small committed reference samples in `pipeline/tests/fixtures/`; ruff and pyright for lint and types.

**Target Platform**: a developer laptop (Windows, macOS or Linux) and Linux CI.

**Project Type**: data pipeline (Python library with a command-line interface) plus an analysis notebook.

**Performance Goals**: full analysis, excluding downloads, in under 30 minutes on the reference machine (SC-008: 4 CPU cores, 16 GB RAM, SSD); `run` records its own runtime in the manifest and warns above the limit. Itinerary pairing runs on schedule patterns, not every daily flight combination (research R6).

**Constraints**: fully deterministic output (stable sort orders, fixed random seed); no network access in tests; free public data only; all times in UTC (ADR-0008).

**Scale/Scope**: about 7–8 million flight records for 12 months; 30 candidate airports; 5–8 selected hubs; 10–15 origin/destination pairs; 27 sensitivity scenarios (3 × 3 × 3).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle / rule | How this plan complies | Status |
|---|---|---|
| I. Statistical honesty | Every result row carries sample size and data period; "insufficient data" below 30 paired days; feasibility wording; significance required for showcases (paired bootstrap); limitations listed in the finding | Pass |
| II. Automated verification | Calculation, time-zone and schema modules are built test-first against committed reference samples; Hypothesis covers time edge cases; no network in tests; notebook holds no logic and has a headless smoke test; the real-data runtime and reproducibility checks are scripted (`run` records runtime, `verify` compares hashes) | Pass |
| III. Thin, deployable slices | Out-of-scope list respected (no UI, API, fares, deployment). Phase 0 has no deployable deliverable, so per constitution v1.1.0 it is done when its roadmap exit criterion (a recorded go/no-go ADR) is met and docs are updated | Pass |
| IV. One data contract | Config and every output table are defined as Pydantic models; output files are validated against them. No TypeScript yet, so type generation starts in Phase 1 | Pass |
| V. Accessible and clear | No UI. Notebook charts use labels and patterns as well as color, and state sample sizes and data periods | Pass |
| VI. Simplicity, replaceable providers | Each data source sits behind a provider interface (`providers/`); a single library package plus a command-line interface; no services or databases | Pass |
| Data and technology constraints | Free data only; raw data out of git; pipeline rebuilds from pinned config; attribution for airportsdata (MIT) and BTS recorded in the report | Pass |
| ADR conformance | Follows ADRs 0002–0005, 0008 and 0009. One change: the time-zone source moves from OpenFlights to airportsdata, recorded in ADR-0011 (accepted 2026-11-24), which supersedes only that part of ADR-0008 | Pass |
| Workflow | Feature branch; spec clarified; this plan awaits owner approval; independent review before merge | Pass |

**Post-design re-check (after Phase 1):** no violations introduced. The data model, contracts and quickstart keep all logic in tested modules, every output table carries sample size and period, and providers remain swappable. **Pass.**

## Project Structure

### Documentation (this feature)

```text
specs/001-bts-connection-experiment/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 research decisions
├── data-model.md        # Entities, fields, validation rules
├── quickstart.md        # How to run and verify
├── contracts/
│   ├── cli.md           # Command-line interface
│   ├── config.md        # Configuration file schema
│   └── outputs.md       # Output tables and report schema
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Created by /speckit-tasks
```

### Source Code (repository root)

```text
pipeline/
├── pyproject.toml                 # uv project; package flight_pipeline; CLI entry point
├── uv.lock
├── src/flight_pipeline/
│   ├── config.py                  # Pydantic config models; TOML loading
│   ├── models.py                  # Pydantic models for every output table (ADR-0007)
│   ├── providers/
│   │   ├── base.py                # Provider interfaces
│   │   ├── bts_ontime.py          # Monthly on-time zip files
│   │   ├── bts_t100.py            # T-100 segment passenger data
│   │   └── timezones.py           # Airport → IANA time zone
│   ├── prepare/
│   │   ├── normalize.py           # Raw CSV → typed flight records (Parquet)
│   │   ├── timeconv.py            # Local schedule + delay minutes → UTC instants
│   │   └── quality.py             # Duplicates, missing times, consistency checks
│   ├── hubs.py                    # Candidate metrics, eligibility, score, constrained selection
│   ├── itineraries.py             # Schedule patterns, recurrence, pairing rules
│   ├── feasibility.py             # Daily outcomes, slack, per-itinerary results
│   ├── od_selection.py            # Origin/destination pair ranking and selection
│   ├── compare.py                 # Comparability, paired bootstrap, showcase rules, go criterion
│   ├── sensitivity.py             # 27 scenarios; assumption-sensitivity flags
│   ├── report.py                  # Summary report and run manifest
│   ├── storage.py                 # Deterministic Parquet writing, model tables (research R8)
│   ├── stages.py                  # One function per CLI stage; reads and writes derived files
│   └── cli.py                     # Command-line stages
└── tests/
    ├── fixtures/                  # Small committed reference samples (CSV) and expected results
    ├── unit/                      # One test module per library module
    └── integration/               # End-to-end run on fixtures; determinism check

config/
└── phase0.toml                    # Pinned configuration for this feature

notebooks/
└── phase0_connection_experiment.py   # marimo notebook; reads outputs only

reports/phase0/                    # Committed summary outputs (small)
data/raw/  data/derived/           # Ignored by git

docs/adr/0011-airport-timezone-source.md   # Proposed with this plan
docs/adr/0012-phase0-go-no-go.md           # Written at the end of implementation
```

**Structure Decision**: the `pipeline/` project follows the repository layout in ADR-0002. It's a library with a thin command-line interface, so Phase 1's `showcase-data-pipeline` can reuse the same modules. The Pydantic models live in `flight_pipeline.models` for now; they move to a shared package when the Phase 2 API needs them, which is a mechanical move recorded at that time.

## Amendment 1: sold routings and connection-level recurrence

Approved by the owner on 2026-11-24 with option A, after independent review rounds 4–5. Spec changes: FR-001, FR-013a, FR-016, FR-018a, FR-025, FR-027 and FR-032; new SC-009 and SC-010; ADR-0013. Decisions: research R10–R12.

**What changes in the pipeline**

| Area | Change |
|---|---|
| Configuration | One period for all sources: `[period]` gets a single `start`/`end` pair (2024-07 to 2025-06), quarter-aligned. New `[sources.db1b]` with URL pattern and per-quarter checksums. `[itineraries]` gains `min_sold_passengers` (default 30) and `carrier_map` (DB1B code to marketing code, default empty) |
| Providers | `providers/bts_db1b.py`: quarterly PREZIP download and checksum, the same pattern as the on-time provider |
| Prepare | `prepare/db1b.py`: extract each quarter, aggregate 2-coupon markets into sold routings with DuckDB, delete the extracted CSV, and report legs with unknown selling airlines. Output: `sold_routings.parquet` |
| Itinerary rules | `itineraries.py`: the R12 order. Candidates, then median layover, then sold routing, then connection-level recurrence. Exclusion counts per rule. New Itinerary fields `connect_share` and `sold_passengers`. Hub eligibility uses the same rules |
| Sensitivity | Itineraries are rebuilt per scenario with the same rules. A new `ComparablePair.settings_compared` counts distinct (minimum connection time, cutoff) settings, out of 9 |
| Report | Per-pair exclusion counts (FR-018a), the DB1B period and sample note, settings compared per showcase, sold passengers per itinerary |
| Docs | Methodology, ADR-0012 rewritten after the rerun, roadmap |

**Constitution Check (re-evaluated):** all principles still pass.
- **Principle I:** every new threshold is documented and every exclusion is counted.
- **Principle II:** new tasks are test-first.
- **Principle VI:** DB1B sits behind a provider interface.
- **Data constraints:** DB1B is free BTS data, and its raw files stay out of git.

**Performance:** DB1B preparation adds about 30 seconds (4 quarters at about 7 seconds each, plus download). Connection-level recurrence runs only on sold routings. The expected full runtime stays under 10 minutes on the development machine.

## Risks

| Risk | Mitigation |
|---|---|
| T-100 has no direct download, only a web form (research R2) | Provider tries the scripted form download; if that fails, the run stops with instructions for a one-time manual download, verified against a SHA-256 checksum pinned in config. Passenger data affects only the hub score |
| Source data periods differ (DB1B is published about 15 months after a quarter ends) | Amendment 1: one quarter-aligned period for all sources, set by the latest DB1B quarter (research R11); recorded in the manifest and report |
| BTS gate-time and `2400` conventions not confirmed by documentation (R3) | UTC instants are computed from scheduled time plus delay minutes, not from actual clock times; quality checks compare against the clock-time fields and report disagreements |
| Too few showcase examples | That is a valid result. The finding records it as no-go or a documented pivot |

## Complexity Tracking

| Deviation | Why it is needed | Simpler alternative rejected because |
|---|---|---|
| Pattern-level layovers (itinerary qualification) use the difference of local times of day at the hub, not UTC (Principle IV, ADR-0008) | Patterns are paired on median schedules across the whole period; local time of day at one airport is stable across daylight-saving changes, while UTC times of day shift by an hour twice a year | Medians of UTC differences need every daily pair, the join research R6 avoids. Daily slack, the measured quantity, is always UTC; on a daylight-saving night a local layover can read up to 60 minutes off, which the median over at least 60% of days absorbs |
