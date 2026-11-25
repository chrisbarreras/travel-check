# Quickstart: BTS Connection Feasibility Experiment

How to run and verify this feature. Commands run from the repository root unless noted.

## Prerequisites

- uv installed (`uv --version`); uv installs Python 3.13 automatically.
- About 6 GB free disk space: 12 months of raw on-time data (zips and extracted CSVs), 4 DB1B quarters (about 110 MB each zipped; each is extracted to about 2 GB during `prepare` and then deleted) plus derived tables.
- For T-100: `acquire` downloads it through the TranStats form by script; if that fails, it prints manual-download steps (see [contracts/cli.md](contracts/cli.md)).

## Setup

```bash
cd pipeline
uv sync
```

## Verify the code (no network, no downloads)

```bash
cd pipeline
uv run pytest                 # unit tests on committed fixtures + end-to-end tests on a generated year
uv run ruff check .
uv run ruff format --check .
uv run pyright
```

**Expected:** all tests pass, including:
- time conversion across midnight, `2400`, time zones and a daylight-saving change;
- hub selection on a fixture with a known expected selection and reasons;
- itinerary rules (marketing vs. operating airline, partner pairs, layover limits, recurrence);
- outcome classification and slack percentiles against hand-computed values;
- the paired bootstrap on synthetic data with a known difference;
- the determinism test (two runs produce identical output hashes) and the `verify` check;
- the notebook running headlessly against pipeline outputs.

## Run the full analysis

```bash
cd pipeline
uv run flight-pipeline run --config ../config/phase0.toml
```

To rerun from raw files already in place without contacting BTS: `uv run flight-pipeline run --no-acquire --config ../config/phase0.toml`.

**Expected:** exit code 0; `reports/phase0/summary.md` lists the selected hubs with reasons, 10–15 origin/destination pairs, results with sample sizes, showcase examples and the go/no-go criteria. `manifest.json` records `runtime_min` (excluding downloads) and `runtime_exceeded: false` (limit 30 minutes, SC-008).

## Check reproducibility (SC-001)

```bash
cd pipeline
uv run flight-pipeline verify --config ../config/phase0.toml
```

**Expected:** exit code 0 and "identical". Any difference in output-table hashes or `summary.json` is listed and the command exits 1.

## View the notebook

```bash
cd pipeline
uv run marimo edit ../notebooks/phase0_connection_experiment.py
```

The notebook only reads `data/derived/phase0/` and `reports/phase0/`; it never recomputes results.

## Finish the feature

1. Write `docs/adr/0012-phase0-go-no-go.md` from `reports/phase0/summary.md`.
2. Run the independent `feature-reviewer` agent and save its report as `review.md` (constitution, workflow section).
