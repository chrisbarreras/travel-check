# Data Model: BTS Connection Feasibility Experiment

Every entity below is a Pydantic model in `flight_pipeline.models` (ADR-0007). Tables are stored as Parquet in `data/derived/phase0/` and validated against these models when written. All instants are UTC (ADR-0008). Sort orders are listed in [contracts/outputs.md](contracts/outputs.md).

## Source-level entities

### FlightRecord
One scheduled flight instance after normalization.

| Field | Type | Notes |
|---|---|---|
| `marketing_airline` | str | From `Marketing_Airline_Network` |
| `operating_airline` | str | From `Operating_Airline`; never used for pairing (FR-014) |
| `flight_number` | int | Marketing flight number |
| `service_date` | date | Local date at the origin (`FlightDate`) |
| `origin`, `dest` | str | IATA codes |
| `sched_dep_utc`, `sched_arr_utc` | datetime (UTC) | Research R3 |
| `sched_dep_local_min`, `sched_arr_local_min` | int, 0–1439 | `CRSDepTime` / `CRSArrTime` as minutes after local midnight at the origin / destination (`2400` → 0). Used for layovers and comparability (time of day), never for elapsed time |
| `sched_elapsed_min` | int | `CRSElapsedTime` |
| `actual_dep_utc`, `actual_arr_utc` | datetime (UTC) or null | Null if cancelled, diverted or missing |
| `cancelled`, `diverted` | bool | |
| `cancellation_code` | str or null | A, B, C or D |
| `weather_delay_min` | int or null | |
| `weather_affected` | bool | `weather_delay_min > 0` or `cancellation_code == "B"` (FR-007) |
| `quality_flag` | enum | `ok`, `duplicate`, `conflicting_duplicate`, `missing_actual_times`, `clock_time_mismatch`. For identical copies, one is `ok` (first by source file and row order) and the rest `duplicate`; when copies of one identity disagree, all are `conflicting_duplicate` (spec Edge Cases) |

**Identity:** (`marketing_airline`, `flight_number`, `service_date`, `origin`). Must be unique among `quality_flag == ok` rows.

**Validation:** `sched_arr_utc > sched_dep_utc`; if not cancelled or diverted and flag is `ok`, actual times are present.

**Invalid schedules:** source rows whose schedule cannot be converted (missing or non-positive `CRSElapsedTime`, invalid `HHMM`) are corrupt records. They are dropped before conversion, never become FlightRecords, and are counted by month as `invalid_schedule` in `quality.json` (2 rows in July 2024 to June 2025; 7,671,287 rows remain).

### PassengerTraffic
Monthly passengers by airport and airline (T-100).

| Field | Type | Notes |
|---|---|---|
| `year`, `month` | int | |
| `origin` | str | |
| `carrier` | str | `UniqueCarrier` |
| `passengers` | int | ≥ 0 |

### SoldRouting (amendment 1, FR-013a)
Aggregated from DB1B Market rows with exactly 2 coupons, summed over the period's quarters.

| Field | Type | Notes |
|---|---|---|
| `origin`, `hub`, `dest` | str | From `AirportGroup` (`ORIGIN:HUB:DEST`) |
| `airline_in`, `airline_out` | str | Selling airline per leg, from `TkCarrierGroup`, after `carrier_map`; legs recorded as `--` are not counted |
| `passengers` | int | ≥ 0; sampled DB1B passengers (a 10% ticket sample) |

**Identity:** (`origin`, `hub`, `dest`, `airline_in`, `airline_out`).

### Airport

| Field | Type | Notes |
|---|---|---|
| `code` | str | IATA |
| `tz` | str | IANA time zone (ADR-0011) |
| `role` | enum | `hub`, `candidate`, `regional`, `other` |

## Hub selection

### HubCandidate
One row per candidate airport (top 30 by departures).

| Field | Type | Notes |
|---|---|---|
| `airport` | str | |
| `departures` | int | Scheduled departures in period |
| `airline_count` | int | Marketing airlines with ≥ 5% of departures |
| `airlines` | list[str] | Those airlines |
| `passengers` | int or null | Null if missing; treated as 0 in score and reported |
| `weather_share` | float | Weather-affected share of departures, 0–1 |
| `weather_share_by_season` | map season → float or null | Seasons from config: winter (Dec–Feb), spring (Mar–May), summer (Jun–Aug), autumn (Sep–Nov). Null (unknown) when the season has no departures or no weather-affected departures (spec Edge Cases); an unknown season can't be the peak |
| `weather_peak_season` | season or `unknown` | |
| `eligible_itineraries` | int | Qualifying itineraries with origin outside the pool (FR-008) |
| `eligible` | bool | `eligible_itineraries ≥ minimum` |
| `score` | float | Weighted sum of 0–1 scaled components |
| `rank` | int | By score descending, then airport code |

### HubSelection
| Field | Type | Notes |
|---|---|---|
| `airport` | str | |
| `selected` | bool | |
| `reason` | enum or null | `score`, `airline_coverage:<airline>`, `weather_winter`, `weather_summer`, `weather_above_median`, `weather_below_median`; null when not selected |

Unmet constraints are a property of the whole selection, not of a row, so they are stored once in `Finding.unmet_constraints`.

**Selection procedure:** take the top N eligible by rank; for each unmet constraint in a fixed order (airline coverage, then winter, summer, above-median, below-median), swap the lowest-ranked hub not needed by any constraint for the best-ranked eligible candidate that fixes it; repeat until all constraints hold or no swap helps (then record unmet constraints).

## Itineraries

### FlightPattern
| Field | Type | Notes |
|---|---|---|
| `marketing_airline`, `flight_number`, `origin`, `dest` | | Identity |
| `scheduled_days` | int | Days scheduled in period, cancellations included |
| `recurrence` | float | `scheduled_days / days_in_period` |

### Itinerary
| Field | Type | Notes |
|---|---|---|
| `itinerary_id` | str | Deterministic: `{origin}-{hub}-{dest}:{airline1}{num1}+{airline2}{num2}` |
| `origin`, `hub`, `dest` | str | |
| `inbound`, `outbound` | FlightPattern identity | |
| `partner_connection` | bool | Airlines differ and are a listed partner pair |
| `median_layover_min` | int | Within [hub minimum, maximum] (FR-015). Median of the daily scheduled layovers (UTC) on the days the two flights connect; rule 2 pre-filters on the difference of the two patterns' median local times |
| `median_travel_min` | int | Origin departure to destination arrival, scheduled; median over the connecting days |
| `median_dep_local_min` | int | Minutes after local midnight at origin; used for comparability (FR-026) |
| `connect_share` | float, 0–1 | Days in the period on which the two flights connect (outbound scheduled within the layover limits after that day's inbound), divided by days in the period; must be ≥ the recurrence threshold (FR-016) |
| `sold_passengers` | int | Sampled DB1B passengers on this routing and airline pair; must be ≥ `min_sold_passengers` (FR-013a) |

**Rules, in order (research R12):** same marketing airline or partner pair (FR-013), never by operating airline (FR-014); each pattern scheduled on at least the recurrence threshold share of days (a necessary condition); median layover within limits (FR-015); sold routing (FR-013a); connection-level recurrence (FR-016).

### OdExclusions (amendment 1, FR-018a)
One row per selected origin/destination pair.

| Field | Type | Notes |
|---|---|---|
| `origin`, `dest` | str | Identity |
| `candidates` | int | Airline-compatible pattern pairs through the selected hubs, each pattern meeting the recurrence threshold on its own |
| `excluded_layover`, `excluded_unsold`, `excluded_recurrence` | int | ≥ 0; removed at each rule, in order |
| `qualifying` | int | `candidates` minus all exclusions |

## Outcomes and results

### DailyOutcome
| Field | Type | Notes |
|---|---|---|
| `itinerary_id`, `service_date` | | Identity (inbound service date) |
| `raw_slack_min` | int or null | `actual_dep_utc(out) − actual_arr_utc(in)`; null when a leg was cancelled or diverted |
| `outcome` | enum | `feasible`, `insufficient_time`, `cancelled`, `diverted` |

**State rule (FR-019 to FR-021):** cancelled (either leg) → `cancelled`; else diverted (either leg) → `diverted`; else `raw_slack_min ≥ cutoff + min_connection` → `feasible`; else `insufficient_time`. Days with no matching outbound instance or failed quality checks produce no row and are counted in `ItineraryResult.excluded_not_connecting` and `ItineraryResult.excluded_quality` (FR-019).

### ItineraryResult
One row per itinerary per sensitivity scenario.

| Field | Type | Notes |
|---|---|---|
| `itinerary_id`, `scenario_id` | | Identity |
| `paired_days` | int | Rows in DailyOutcome for this itinerary and scenario |
| `excluded_not_connecting` | int | ≥ 0; days with no outbound instance in the layover window |
| `excluded_quality` | int | ≥ 0; days where either leg failed a quality check |
| `feasibility_rate` | float or null | Null when `paired_days < minimum` |
| `status` | enum | `ok`, `insufficient_data` |
| `count_feasible`, `count_insufficient_time`, `count_cancelled`, `count_diverted` | int | |
| `slack_min`, `slack_p10`, `slack_p50`, `slack_p90` | int or null | Over non-null `raw_slack_min`; discrete "lower" rule: sorted ascending, value at index floor(q × (n − 1)), so every value is an observed minute |
| `period_start`, `period_end` | date | |

### SensitivityScenario
| Field | Type | Notes |
|---|---|---|
| `scenario_id` | str | e.g. `mct30_cut15_rec60` |
| `min_connection_min`, `boarding_cutoff_min`, `recurrence_threshold` | | |
| `is_default` | bool | Exactly one is true |

### OdSelection
| Field | Type | Notes |
|---|---|---|
| `origin`, `dest` | str | |
| `comparable_pairs` | int | Under default scenario |
| `main_hub` | str | Hub of the largest share of the pair's itineraries |
| `regional_origin` | bool | |
| `rank`, `selected` | int, bool | |

### ComparablePair
| Field | Type | Notes |
|---|---|---|
| `itinerary_a`, `itinerary_b` | str | `a` has the higher default feasibility rate; if either rate is null or they are equal, `a` is the smaller `itinerary_id` |
| `travel_diff_min`, `dep_diff_min` | int | Within tolerances (FR-026) |
| `rate_diff` | float or null | Default scenario |
| `shared_days` | int | ≥ 0; dates on which both itineraries have a paired outcome (default scenario). A showcase needs at least `min_sample_days` |
| `settings_compared` | int | ≥ 0 (at most 9 with the default lists); distinct (minimum connection time, boarding cutoff) settings, including the default, at which both itineraries had sufficient data in some recurrence scenario. The robustness measure reported for showcases |
| `scenarios_compared` | int | ≥ 0; non-default scenarios in which both itineraries qualified with sufficient data, so the order could be checked (FR-028) |
| `ci_low`, `ci_high` | float or null | Paired bootstrap (research R5) |
| `assumption_sensitive` | bool | Order reverses in any scenario (FR-028) |
| `showcase` | bool | FR-029 conditions all true, including `shared_days` ≥ `min_sample_days` |

### Finding
One object, written as `reports/phase0/summary.json`; the source for `summary.md` and the go/no-go ADR.

| Field | Type | Notes |
|---|---|---|
| `ontime_period_start`, `ontime_period_end` | date | On-time data period (FR-001) |
| `t100_period_start`, `t100_period_end` | date | Passenger data period (FR-001); equal to the on-time period since amendment 1 |
| `db1b_quarters` | list[str] | e.g. `2024-3` … `2025-2` |
| `db1b_unknown_airline_share` | float | Share of 2-coupon sampled passengers not counted because a leg's selling airline is `--` |
| `db1b_unmapped_airlines` | dict[str, int] | Selling-airline codes (after `carrier_map`) that are not on-time marketing airlines, with sampled passengers on routings using them (spec edge case); these routings are not counted |
| `db1b_unmapped_airline_share` | float | Share of 2-coupon sampled passengers on such routings, each routing counted once |
| `airline_coverage` | list[AirlineCoverage] | Per marketing airline: itineraries through the selected hubs (by inbound airline) and sampled DB1B passengers on sold same-airline routings through them |
| `showcase_breakdown` | ShowcaseBreakdown or null | Subsets the decision cites (SC-010): examples per pair, cross-hub examples, examples, pairs and hubs without tight layovers, examples slower than 1.5 times the median nonstop time and the largest ratio, examples without a nonstop, and examples per missing-settings note. Null when there are no examples |
| `od_exclusions` | list[OdExclusions] | Selected pairs only |
| `hubs` | list[HubSelection] | Selected hubs only, with reasons |
| `unmet_constraints` | list[str] | Empty when all hub constraints hold (FR-011) |
| `od_pairs` | list[OdSelection] | Selected pairs only |
| `od_pairs_without_itineraries` | list[str] | `"ORIGIN-DEST (scenario_id)"`, one entry per selected pair and scenario without a qualifying itinerary (FR-018) |
| `default_results` | list[ItineraryResult] | Default scenario only |
| `showcase_examples` | list[ComparablePair] | Rows with `showcase` true |
| `criterion_min_examples_met` | bool | ≥ `go_min_examples` showcase examples (FR-030) |
| `criterion_min_hubs_met` | bool | Examples span ≥ `go_min_hubs` hubs (FR-030) |
| `decision` | enum | `go`, `no_go`, `pivot`. The pipeline sets `go` or `no_go`; `pivot` is set only by the analyst in the ADR |
| `ci_method` | str | Description of the interval method (FR-029) |
| `limitations` | list[str] | Must include the four FR-032 items |
| `data_quality` | map str → int | Totals from `quality.json` |
