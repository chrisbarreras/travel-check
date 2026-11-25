# Contract: Command-Line Interface

Entry point: `flight-pipeline` (run from `pipeline/` with `uv run flight-pipeline ...`). Every command takes `--config PATH` (default `../config/phase0.toml`). `acquire` and `prepare` also take `--month YYYY-MM` (repeatable) to limit on-time data to some months of the period, for checks such as task T028; a month outside the period is a validation error.

| Command | Does | Reads | Writes |
|---|---|---|---|
| `acquire` | Downloads on-time, T-100 and DB1B (quarterly market) files for the configured periods; verifies checksums when pinned and prints the SHA-256 of any unpinned file | network, config | `data/raw/`, including `data/raw/sources.json` (file, URL, SHA-256, pinned) |
| `prepare` | Normalizes flights to UTC; runs quality checks; loads time zones; aggregates DB1B sold routings | `data/raw/` | `data/derived/phase0/flights.parquet`, `passengers.parquet`, `sold_routings.parquet`; `reports/phase0/quality.json` (written even when the quality gate fails) |
| `select-hubs` | Computes candidate metrics and selects hubs | prepared data | `hub_candidates.parquet`, `hub_selection.parquet` |
| `build` | Builds patterns and itineraries; selects origin/destination pairs | prepared data, hub selection | `itineraries.parquet`, `od_selection.parquet` |
| `analyze` | Daily outcomes, results for all scenarios, comparable pairs, showcases | the above | `daily_outcomes.parquet`, `itinerary_results.parquet`, `comparable_pairs.parquet` |
| `report` | Writes the summary report and run manifest | all derived tables | `reports/phase0/summary.json`, `summary.md`, `manifest.json` |
| `run` | Runs all stages in order; skips `acquire` downloads already present and verified; records the runtime excluding downloads in the manifest | | all of the above |
| `verify` | Reproducibility check (SC-001): reruns every stage after `acquire` into a temporary directory and compares output-table hashes and `summary.json` with the committed `reports/phase0/`; exits `0` when identical, `1` listing each difference | `data/raw/`, `reports/phase0/` | nothing outside the temporary directory |

## Behavior

- **Exit codes:** `0` success; `1` validation or data-quality failure (for example, a missing time zone, a header mismatch or a high clock-time disagreement rate); `2` acquisition failure, with manual-download instructions for T-100.
- **Output:** progress on stderr; a one-line result summary on stdout.
- **Determinism:** identical inputs and config produce byte-identical Parquet tables and reports (except the manifest's run-specific fields, `run_at`, `runtime_min`, `runtime_exceeded` and the machine description, which are excluded from output hashes).
- **No hidden state:** each stage reads only its declared inputs.
