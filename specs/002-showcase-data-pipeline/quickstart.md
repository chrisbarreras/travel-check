# Quickstart: Showcase Data Pipeline

How to build, check and verify the showcase data. Contracts: [outputs](contracts/outputs.md), [config](contracts/config.md), [CLI](contracts/cli.md).

## Prerequisites

- uv (installs Python 3.13) and Node.js 20 or later (for type generation only).
- About 6 GB of free disk space: the same pinned BTS sources as Phase 0, July 2024 – June 2025.

## Build

```bash
cd pipeline
uv sync
uv run flight-pipeline run --config ../config/phase1.toml   # downloads if needed, then every stage
uv run flight-pipeline schemas                               # JSON Schema and TypeScript types
```

To time a run as on the 4-core reference machine (SC-008), set `FLIGHT_PIPELINE_THREADS=4`: it limits DuckDB's threads and the bootstrap worker processes. Outputs never depend on it.

**Expected:** `site-data/showcase/index.json`, `landing.json` and 8–12 files in `routes/`, within the size budget; `shared/schemas/showcase.schema.json` and `shared/types/showcase.ts`. The run's summary line states the routes, itineraries and showcase comparisons, the per-airline coverage, and the runtime.

## Check

```bash
uv run ruff check . && uv run ruff format --check . && uv run pyright
uv run pytest                                                # unit, integration, shared test cases
uv run flight-pipeline schemas --check                       # fails if the committed types are stale
```

## Verify

```bash
uv run flight-pipeline verify --config ../config/phase1.toml
```

**Expected:** "identical: N outputs match the committed manifest", including every file in `site-data/showcase/` and the generated types. Editing any committed showcase file by hand makes it fail and name the file (SC-006).

## Validation scenarios

| Scenario | How | Expected |
|---|---|---|
| Renumbered flights form one itinerary (US1) | Unit test on the slot fixture | One slot and one itinerary across days with different flight numbers |
| Layover by daily matching only (US1) | Unit test on the schedule-change fixture | Qualifies; median layover from connecting days |
| Airline coverage (SC-001) | `index.json` → `coverage.airlines` | Southwest and the other major networks have itineraries, or a stated reason |
| Balance (SC-002) | `index.json` → `routes[].share_of_showcase` | No route above one third; at least half the comparisons cross-hub |
| Slider data reproduces the rate (SC-004) | Shared test cases and an integration test over every curated itinerary | Recomputed rate equals the published rate exactly |
| Faster alternatives (SC-005) | Integration test | Every listed alternative meets the equivalence rule |
| Size (SC-007) | `publish` output | Compressed total ≤ 2 MB; `landing.json` loadable alone |
| Reproducibility (SC-006) | `verify` | Identical |

## Reproducing Phase 0

Phase 0's results are frozen at the git tag `phase0-final`:

```bash
git checkout phase0-final
cd pipeline && uv run flight-pipeline verify --config ../config/phase0.toml
```
