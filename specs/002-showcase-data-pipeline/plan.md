# Implementation Plan: Showcase Data Pipeline

**Branch**: `002-showcase-data-pipeline` | **Date**: 2026-11-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-showcase-data-pipeline/spec.md` (approved by the owner with its default assumptions).

## Summary

Extend the Phase 0 pipeline into the data source for the Phase 1 explorer. Four changes of substance:

1. **Itinerary identity by schedule** (research R1): flights are grouped into schedule slots by airline, route and departure-time window, so airlines that renumber flights (Southwest) are covered; an itinerary is two slots through a hub.
2. **Layover limits only through daily matching** (R2), behind a lossless bound pre-filter, with end-of-period days excluded rather than counted as not connecting.
3. **Curation and traveler insights** (R4, R8–R14): a balanced showcase of 8–12 routes with a landing example; per itinerary the faster alternatives (equivalence test), connecting options, buffer, failure types, monthly view with sourced disruption notes, schedule warnings and find-link parameters; nonstop comparison (R3).
4. **A published data contract** (R5–R7): validated, size-budgeted JSON in `site-data/showcase/`, a generated JSON Schema and TypeScript types in `shared/`, shared test cases for the in-browser slider calculation, and `verify` extended to all of it.

Phase 0's results stay frozen at the tag `phase0-final` (R15); Phase 1 runs from a new `config/phase1.toml`.

## Technical Context

**Language/Version**: Python 3.13 with uv (ADR-0002); Node.js 20+ only to run the pinned TypeScript generator.

**Primary Dependencies**: as Phase 0 (DuckDB, Pydantic v2, NumPy, httpx, airportsdata, tzdata); added: `json-schema-to-typescript` (exact version, through `npx`), used only by the `schemas` command and its CI check.

**Storage**: Parquet with DuckDB for internal tables (`data/derived/phase1/`, git-ignored); committed JSON outputs in `site-data/showcase/` and `shared/` (ADR-0009: small derived data is committed).

**Testing**: pytest and Hypothesis, reference fixtures extended with a renumbering airline and schedule changes; a synthetic year extended for curation and insights; shared JSON test cases for the slider calculation; ruff and pyright; `schemas --check` in CI.

**Target Platform**: developer laptop and Linux CI.

**Project Type**: data pipeline (Python library and command line) producing static files for a web front end.

**Performance Goals**: full run, excluding downloads, under 30 minutes on the 4-core reference machine (SC-008); estimate 10–15 minutes on the development machine (R16).

**Constraints**: deterministic byte-identical outputs; no network in tests; free pinned BTS sources only; UTC for all measured times (ADR-0008); published data within 2 MB compressed (SC-007).

**Scale/Scope**: about 7.7 million flight records; 30 candidate hubs, 5–8 selected; 8–12 showcase routes with up to 12 itineraries each (about 100 itineraries × 365 days of slack).

## Constitution Check

*GATE: checked before research and again after design.*

| Principle | How the plan complies |
|---|---|
| **I. Statistical honesty** | Every published rate is a `Rate` with status, sample and period; "insufficient data" carries no number; monthly rates have their own documented minimum (R11); disruption notes are kept apart from measured values (R12); wording is historical, checked by a test over all published text. Sub-minimum counts (allowed since v1.2.0) are not used in Phase 1. Separate measures stay separate (connection feasibility, failure types). |
| **II. Automated verification** | Test-first for slot identity, daily matching, curation, insights and the published shapes; shared test cases for the in-browser calculation (R7); deterministic tests without network; `verify` covers every output. |
| **III. Thin slices** | This feature only produces data; the frontend features follow. Out of scope stated in the spec. |
| **IV. One data contract** | Pydantic models are the only definition; JSON Schema and TypeScript types are generated and checked in CI (R6, ADR-0007); measured times are UTC. |
| **V. Accessible and clear** | Sets this phase's data budget (2 MB compressed, landing file alone); every value has a definition entry for the explorer to display. |
| **VI. Simplicity, replaceable providers** | No new data sources; the providers are unchanged; one new tool (the TypeScript generator), recorded below. |

**Result**: passes, with the deviations recorded in Complexity Tracking. Re-checked after design: unchanged.

## Project Structure

### Documentation (this feature)

```text
specs/002-showcase-data-pipeline/
├── spec.md
├── plan.md              # this file
├── research.md          # R1–R16
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── outputs.md
│   ├── config.md
│   └── cli.md
└── tasks.md             # next: /speckit-tasks
```

### Source code (repository root)

```text
config/
├── phase0.toml                      # unchanged (frozen Phase 0)
├── phase1.toml                      # new
└── disruption_notes.toml            # new, curated and sourced

pipeline/src/flight_pipeline/
├── slots.py                         # new: schedule slots and slot days (R1)
├── itineraries.py                   # changed: slot pairs, bound pre-filter, daily matching only (R2)
├── nonstop.py                       # new: nonstop medians (R3)
├── curation.py                      # new: showcase routes, caps, landing example (R4)
├── insights/                        # new
│   ├── alternatives.py              # faster alternatives (R8), connecting options (R9)
│   ├── buffer.py                    # R10
│   ├── monthly.py                   # R11, disruption notes (R12)
│   └── schedule.py                  # schedule changes (R13), find parameters (R14)
├── showcase/                        # new: published Pydantic models and writer
│   ├── models.py
│   └── publish.py                   # stable JSON, validation, size budget, manifest (R5)
├── schemas.py                       # new: JSON Schema export and type generation (R6)
├── stages.py, cli.py, config.py     # changed: new stages and commands, phase1 config
└── (Phase 0 modules reused)

pipeline/tests/
├── fixtures/                        # + renumbering airline, schedule changes, disruption notes
├── unit/                            # + test_slots, test_bounds, test_curation, test_alternatives,
│                                    #   test_buffer, test_monthly, test_schedule_changes, test_publish
└── integration/                     # + synthetic showcase run, determinism, shared test cases

shared/
├── schemas/showcase.schema.json     # generated, committed
├── types/showcase.ts                # generated, committed
└── test-cases/slack-feasibility.json

site-data/showcase/                  # published, committed
└── index.json, landing.json, routes/*.json, manifest.json

.github/workflows/pipeline.yml       # + Node setup and `schemas --check`
```

**Structure decision**: the existing single Python project is extended. `shared/` holds the cross-language contract, so neither the pipeline nor the future `web/` owns it. `site-data/` holds the published data the web app will serve.

## Phase 0 freeze

Before the first change to pipeline behaviour, tag the merge commit that produced `reports/phase0/` as `phase0-final` and record it in ADR-0012's evidence line and the README. `reports/phase0/` stays as the record. (A tag is a lightweight git action; it is pushed with the first implementation push.)

## Complexity Tracking

| Deviation | Why it is needed | Simpler alternative rejected because |
|---|---|---|
| A Node.js tool in the pipeline's CI and `schemas` command | ADR-0007 requires TypeScript types generated from the models' JSON Schema, and the maintained generator is a Node package | Hand-written types are forbidden (Principle IV); Python-only generators wrap the same Node tool |
| Schedule slots cluster by **local** time of day (Principle IV, ADR-0008) | A traveler's "2 pm flight" is a local time, and local times stay stable across daylight-saving changes while UTC times shift an hour | Clustering by UTC splits one schedule into two slots twice a year. Every measured quantity (slack, layover, travel time) stays UTC |
| Phase 0 reproduced from a tag, not from the current code | The identity and layover rules change by design (ADR-0012) | A permanent second code path for a decided analysis doubles rules and tests |
