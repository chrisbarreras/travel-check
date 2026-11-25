# Contract: Outputs

Field definitions are in [../data-model.md](../data-model.md). This file fixes file locations, sort orders and what is committed.

## Derived tables (`data/derived/phase0/`, not committed)

| File | Model | Sort order |
|---|---|---|
| `flights.parquet` | FlightRecord | every FlightRecord column, in model order (a total order, so even conflicting copies have a fixed position) |
| `passengers.parquet` | PassengerTraffic | year, month, origin, carrier |
| `airports.parquet` | Airport | code |
| `sold_routings.parquet` | SoldRouting | origin, hub, dest, airline_in, airline_out |
| `od_exclusions.parquet` | OdExclusions | origin, dest |
| `hub_candidates.parquet` | HubCandidate | rank |
| `hub_selection.parquet` | HubSelection | selected desc, airport |
| `itineraries.parquet` | Itinerary | itinerary_id |
| `od_selection.parquet` | OdSelection | rank |
| `sensitivity_scenarios.parquet` | SensitivityScenario | scenario_id |
| `daily_outcomes.parquet` | DailyOutcome | itinerary_id, service_date (default scenario only) |
| `itinerary_results.parquet` | ItineraryResult | scenario_id, itinerary_id |
| `comparable_pairs.parquet` | ComparablePair | itinerary_a, itinerary_b |

Stage metadata in the same directory (JSON, not committed): `hub_selection.json` (candidate pool, selected hubs, unmet constraints, pool median weather share), `od_selection.json` (selection shortfalls), `sensitivity.json` (pairs without qualifying itineraries per scenario; pair-scenario combinations that could not be compared) and `sensitivity_summary.json` (per-scenario counts, median connection feasibility and reversals, read by the notebook). `acquire` writes `data/raw/sources.json` (file, URL, SHA-256, pinned).

## Committed reports (`reports/phase0/`)

| File | Contents |
|---|---|
| `summary.json` | The Finding model: periods, hub selection with reasons, unmet constraints, selected pairs, per-itinerary default results, showcase examples, criteria and decision, limitations |
| `summary.md` | The same content as readable tables (the strongest showcase example per pair; all default results in an appendix), used to write the go/no-go ADR |
| `manifest.json` | Config SHA-256, source file SHA-256s, package versions, SHA-256 of every derived table and report file (byte-identical by design, research R8), and the run-specific fields `run_at`, `runtime_min` (excluding downloads), `runtime_exceeded` and machine description (CPU count, RAM), which are excluded from hashing |
| `quality.json` | Duplicate, missing-time and clock-mismatch counts by month |

These files are small (well under the ADR-0009 size budget) and let reviewers audit results without downloading data.

## Reporting rules

- Every reported rate is shown with `paired_days` and the data period.
- Itineraries with `status = insufficient_data` show "insufficient data" and no rate.
- Wording uses "connection feasibility", never "made their connection" or other passenger-outcome language (FR-032).
- Attribution for BTS data and airportsdata (MIT) appears in `summary.md`.
