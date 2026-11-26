# Data Model: Showcase Data Pipeline

Every shape below is a Pydantic model (ADR-0007), the single definition. Internal tables are Parquet under `data/derived/phase1/`; the published files are JSON under `site-data/showcase/` (contracts/outputs.md). Times are UTC instants unless named `*_local_min` (minutes after local midnight, for display and clustering only; ADR-0008). Phase 0 entities ([specs/001 data-model](../001-bts-connection-experiment/data-model.md)) are reused where not replaced here.

## Internal tables

### ScheduleSlot (replaces FlightPattern)
| Field | Type | Notes |
|---|---|---|
| `slot_id` | str | `{airline}-{origin}-{dest}-{HHMM}`; HHMM = reference local departure, with `-2`, `-3` on collision |
| `marketing_airline`, `origin`, `dest` | str | |
| `ref_dep_local_min` | int 0–1439 | Median local departure minute of the slot's days |
| `min_dep_local_min`, `max_dep_local_min` | int | Range over the period (bound pre-filter, research R2) |
| `scheduled_days` | int | Days scheduled in the period, cancellations included |
| `recurrence` | float 0–1 | `scheduled_days / days_in_period` |
| `flight_numbers` | list[FlightNumberShare] | Every flight number seen, with its share of the slot's days, sorted by share |

### SlotDay
One row per flight-day assigned to a slot: `slot_id`, `service_date`, the FlightRecord identity (airline, flight number, origin, date). **Identity:** (`slot_id`, `service_date`), unique (research R1, step 3).

### Itinerary (replaces Phase 0's Itinerary)
| Field | Type | Notes |
|---|---|---|
| `itinerary_id` | str | `{origin}-{hub}-{dest}:{airline}{HHMM}+{airline}{HHMM}` from the two slots |
| `origin`, `hub`, `dest` | str | |
| `inbound_slot`, `outbound_slot` | str | slot_ids |
| `partner_connection` | bool | |
| `median_layover_min`, `median_travel_min` | int | Over connecting days, from daily UTC schedules |
| `median_dep_local_min` | int 0–1439 | Inbound slot reference |
| `connect_share` | float 0–1 | Connecting days / eligible days; ≥ recurrence threshold |
| `eligible_days` | int | Days in the period minus end-of-period exclusions (research R2) |
| `sold_passengers`, `routing_itineraries` | int | DB1B routing total and how many itineraries share it |
| `nonstop_median_min` | int or null | Pair's typical nonstop time; null when none |
| `nonstop_ratio` | float or null | `median_travel_min / nonstop_median_min`, rounded to 0.1 |

Phase 0's DailyOutcome, ItineraryResult, ComparablePair, SensitivityScenario and OdExclusions are kept, keyed by the new `itinerary_id`; OdExclusions replaces `excluded_layover` with `excluded_bounds` (lossless pre-filter) and `excluded_not_connecting` (never connects within the limits).

## Published entities (JSON)

### ShowcaseIndex (`index.json`)
| Field | Type | Notes |
|---|---|---|
| `schema_version` | str | Semantic version of these shapes |
| `period` | DataPeriod | `start`, `end`, `db1b_quarters` |
| `assumptions` | Assumptions | Minimum connection time (default, partner), boarding cutoff, recurrence, minimum sample, monthly minimum, buffer share, faster-alternative margin and minimum saving |
| `coverage` | Coverage | FR-015a |
| `balance` | Balance | FR-008: `caps` (`route`, `airline`, `hub`, `cross_hub_min`), `airline_shares`, `hub_shares`, `cross_hub_share`, `shortfalls[]` |
| `routes` | list[RouteSummary] | One per showcase route |
| `landing` | LandingRef | Route and comparison IDs, selection reason |
| `definitions` | list[Definition] | `key`, `text`, `methodology_anchor`: every measure the files use |
| `attribution` | list[Attribution] | `source`, `text`, `licence`, `url`: BTS (on-time, DB1B, T-100), airportsdata and tzdata; the explorer displays them (constitution, data licences) |
| `manifest` | ManifestRef | Package version, config checksum and the manifest's path; the git commit and run times are only in `manifest.json`, so the published bytes do not change with every code commit |

### Coverage
`routes` (list of `ORIGIN-DEST`), `hubs`, `airlines` (each with itinerary count and sold passengers through the hubs), `period`, and `not_covered`: a list of `{kind, text}` with kinds `international`, `two_or_more_stops`, `separate_tickets`, `non_reporting_airline`, `outside_period`, `not_in_showcase`.

### RouteSummary
`route_id` (`ORIGIN-DEST`), origin and destination codes and names, `regional_origin`, `itinerary_count`, `comparison_count`, `share_of_showcase`, `nonstop_median_min` or null, `file` (relative path).

### RouteFile (`routes/{ORIGIN}-{DEST}.json`)
`route_id`, `period`, `itineraries` (list[ShowcaseItinerary]), `comparisons` (list[ShowcaseComparison]), `disruption_notes` (list[DisruptionNote], only those matching the route).

### ShowcaseItinerary
| Field | Type | Notes |
|---|---|---|
| `itinerary_id`, `hub`, `airline` / `airline_out` | str | |
| `min_connection_min` | int | This itinerary's minimum connection time (hub, partner rule): the slider's default transfer time |
| `schedule` | Schedule | Reference local departure and arrival, median layover and travel time, nonstop comparison |
| `result` | Rate | Default-assumption result (below) |
| `failures` | FailureBreakdown | `too_little_time`, `cancelled`, `diverted`, `dominant` |
| `daily` | DailySeries | Columnar, one entry per paired day: `day_offset[]`, `slack_min[]` (actual minutes from inbound arrival to outbound departure; null when cancelled or diverted), `outcome` as one string of codes (`F` feasible, `T` too little time, `C` cancelled, `D` diverted, at the default assumptions). A day is feasible at transfer time T when its code is not C or D and `slack_min` ≥ T + boarding cutoff (shared/test-cases/slack-feasibility.json). **Validation:** one entry per `result.paired_days`; the code counts equal `result.count_feasible` and the `failures` counts |
| `excluded_days` | ExcludedDays | `not_connecting`, `quality`, `end_of_period` |
| `monthly` | list[MonthRate] | 12 entries: `month`, `status` (`ok`, `insufficient_data`, `no_flights`), `rate` or null, `paired_days`, `note_ids[]` |
| `buffer` | Buffer | `share` (0.95), `needed_layover_min`, `actual_layover_min` (the median scheduled layover), `scheduled_at_least_share` (operated days scheduled with at least the recommendation), `operated_days` |
| `faster_alternatives` | list[Alternative] | Research R8; empty list means none |
| `connecting_options` | list[ConnectingOption] | Research R9 |
| `schedule_warnings` | ScheduleWarnings | `connect_share` with `connecting_days` and `eligible_days`, `changes[]` (`date`, `leg`, `from_local_min`, `to_local_min`) |
| `find` | FindParams | `origin`, `dest`, `airlines[]`, `legs[]` (`flight_number`, `share_of_days`) |
| `tight_layover` | bool | Median layover below minimum connection time plus cutoff |
| `sold` | SoldRouting | `passengers`, `routing_itineraries` |

Results under the other assumption scenarios (minimum connection time, cutoff, recurrence) stay internal (`itinerary_results.parquet`). The published data carries the default result, the daily series for the transfer-time slider, and, per comparison, `settings_compared` and `missing_settings_note`.

### Rate
`status` (`ok` or `insufficient_data`), `rate` (float 0–1, or null when insufficient), `paired_days`, `count_feasible`, `definition` (`connection_feasibility`). The data period is the containing file's `period` (every rate in a file shares it). **Validation:** `rate` is null exactly when `status` is `insufficient_data`; `paired_days` ≥ minimum when `ok`.

### ShowcaseComparison
`comparison_id`, `itinerary_a` (higher rate), `itinerary_b`, `difference` and `ci_low`/`ci_high` (points, whole numbers in display, 6 decimals stored), `shared_days`, `settings_compared`, `missing_settings_note`, `cross_hub`, `landing` (bool).

### Alternative
`itinerary_id`, `minutes_saved`, `rate_this` and `rate_other` (each a Rate, with its sample), `ci_low`, `ci_high`, `shared_days`. **Validation:** `ci_low` ≥ −margin; `minutes_saved` ≥ minimum saving.

### ConnectingOption
`itinerary_id`, `outbound_dep_local_min`, `rate` (Rate), `better` (bool), `ci_low`/`ci_high` (vs this itinerary) or null.

### DisruptionNote
`note_id`, `start`, `end`, `airlines[]`, `airports[]`, `text`, `source_url`. From `config/disruption_notes.toml`; never used in a calculation.

### ShowcaseManifest (`site-data/showcase/manifest.json`)
Sources and their checksums, config checksum, disruption-notes checksum, code version (package version and git commit), package versions, output checksums, and the run block (runtime, measured-at, machine) with Phase 0's carry-over rule extended to the code version (FR-027). Written by `publish` and, with the measured runtime, by `run`. `verify` compares every other published file byte for byte and the manifest by its input identities (config, notes, sources, packages).

## Relationships

- ScheduleSlot 1–n SlotDay; Itinerary = two ScheduleSlots through a hub.
- RouteFile 1–n ShowcaseItinerary, 1–n ShowcaseComparison; ShowcaseIndex 1–n RouteSummary.
- Alternative, ConnectingOption and ShowcaseComparison refer to itineraries on the same route file.
- MonthRate `note_ids` refer to DisruptionNote entries in the same route file.
