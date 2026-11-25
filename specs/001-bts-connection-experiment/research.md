# Research: BTS Connection Feasibility Experiment

Each entry records a decision, why it was made, and the alternatives considered. Sources were checked on 2026-11-24.

## R1. On-time data source and period

- **Decision:** use the BTS **Marketing Carrier On-Time Performance (Beginning January 2018)** dataset, downloaded as monthly pre-zipped files:
  `https://www.transtats.bts.gov/PREZIP/On_Time_Marketing_Carrier_On_Time_Performance_Beginning_January_2018_{YYYY}_{M}.zip`
  (month not zero-padded). The period is **October 2025 – September 2026**, the latest 12 months available ("Latest Available Data: September 2026"). Amendment 1 replaces this with July 2024 – June 2025, the latest period DB1B also covers (R11).
- **Rationale:** this dataset has both the marketing airline (`Marketing_Airline_Network`) and the operating airline (`Operating_Airline`), which ADR-0004 requires. Pre-zipped monthly files are a stable, scriptable download.
- **Known irregularity:** at least one file (2023-12) uses a different name with parentheses. The provider takes the file name pattern from config and allows per-month overrides; it records each file's SHA-256 in the run manifest.
- **Alternatives considered:** the Reporting Carrier dataset (lacks consistent marketing-airline fields for regional flights); the field-selection web form (not scriptable reliably).

### Fields used

| Purpose | Field |
|---|---|
| Marketing airline | `Marketing_Airline_Network` |
| Operating airline | `Operating_Airline` |
| Marketing flight number | `Flight_Number_Marketing_Airline` |
| Service date | `FlightDate` |
| Airports | `Origin`, `Dest` |
| Scheduled times (local HHMM) | `CRSDepTime`, `CRSArrTime` |
| Actual times (local HHMM) | `DepTime`, `ArrTime`, used only for consistency checks (R3) |
| Delay and elapsed minutes | `DepDelay`, `ArrDelay`, `CRSElapsedTime`, `ActualElapsedTime` |
| Status | `Cancelled`, `CancellationCode` (A = carrier, B = weather, C = National Air System, D = security), `Diverted`, `Duplicate` |
| Delay causes | `WeatherDelay`, `NASDelay` (NAS is read but not used for weather, per clarification) |

Column names come from the BTS field documentation. The normalizer validates the actual CSV header against this list and fails with a clear error if a name differs.

**Verified on real data (2026-09 file, 630,177 rows, task T028):** all fields above are present. The header writes `Operating_Airline ` with a trailing space, and every line ends with a trailing comma (an empty extra column), so names are compared after trimming. Times are zero-padded `HHMM` strings; numbers are written as `-4.00`; an empty `CancellationCode` is an empty string. The `Duplicate` column is `N` on every row, and the identity (marketing airline, flight number, date, origin) is unique in the month; the pipeline still detects duplicates itself. Eight marketing networks appear (AA, DL, UA, WN, AS, B6, F9, G4). Across all 12 months, 19 rows have a missing or negative `CRSElapsedTime` (for example −60 minutes); they are dropped and counted as `invalid_schedule` instead of stopping the run.

## R2. Passenger volume source (T-100)

- **Decision:** use **T-100 Domestic Segment (U.S. Carriers)**: `Passengers` summed by `Origin` over 12 months (passengers boarded at the airport), with `UniqueCarrier`, `Year` and `Month`. The latest available month is August 2026, so the T-100 period is **September 2025 – August 2026**.
- **Acquisition:** T-100 has no pre-zipped file. The provider (behind the provider interface) first attempts the scripted TranStats download. If that fails, the run stops and prints instructions for a one-time manual download into `data/raw/t100/`, and the file is verified against a SHA-256 checksum pinned in config. This keeps the run reproducible even when it can't be fully automated.
- **Rationale:** the spec requires BTS T-100 data. Passenger volume only affects the hub score, so a one-month offset from the on-time period is acceptable and is reported.
- **Alternatives considered:** FAA annual enplanement reports (calendar-year only, Excel format, and a different source than the spec names); dropping passenger volume (rejected by the user's criteria).
- **Verified (task T028):** the scripted download works. The TranStats form (`DL_SelectFields.aspx?gnoyr_VQ=FIM`) is an ASP.NET page; posting its hidden state fields with `cboYear`, `cboPeriod` (month), Geography `All` and the five field checkboxes returns a zip holding `T_T100D_SEGMENT_US_CARRIER_ONLY.csv` and `Documentation.csv`. The header is `PASSENGERS,UNIQUE_CARRIER,ORIGIN,YEAR,MONTH`. The provider requests the 12 months one by one (about one minute) and writes them as one combined CSV (458,862 rows for 2025-09 to 2026-08). Each generated zip carries a fresh timestamp, so the checksum is pinned on the combined CSV, not the zips. The manual download remains the fallback if the form changes.
- **Checksum rule (both sources):** a pinned checksum must match or the run fails; an unpinned file is accepted, its SHA-256 is printed and recorded in `sources.json`, and it should then be pinned.

## R3. Computing UTC instants without guessing dates

- **Decision:** compute instants from the **scheduled departure plus minute offsets**, not from actual clock times:
  - scheduled departure (UTC) = `FlightDate` + `CRSDepTime`, in the origin's time zone, converted to UTC
  - scheduled arrival (UTC) = scheduled departure + `CRSElapsedTime`
  - actual gate departure (UTC) = scheduled departure + `DepDelay`
  - actual gate arrival (UTC) = actual gate departure + `ActualElapsedTime`
  - `CRSDepTime` values of `2400` are treated as 00:00 on the next day.
- **Rationale:** actual clock times (`DepTime`, `ArrTime`) give no date, so a delayed 23:30 departure that leaves at 00:30 is ambiguous. Minute offsets are unambiguous and cross midnight, time zones and daylight-saving changes correctly. The BTS documentation read did not confirm the `2400` convention, so the code handles both `0000` and `2400`.
- **Gate vs. runway times:** BTS delay statistics are defined on gate departure and arrival; wheels-off and wheels-on are separate fields. The documentation read did not state this explicitly, so a quality check compares the computed instants with `DepTime`/`ArrTime` and reports the share that disagree by more than 1 minute. A high disagreement rate fails the run.
- **Alternatives considered:** rolling the date forward when the arrival clock time is earlier than departure (fails for long delays and certain time-zone combinations).
- **Verified on real data (2026-09, task T028):** `CRSDepTime` never uses `2400`, but `DepTime` (53 rows) and `ArrTime` (264 rows) do, for actual midnight; both are handled. Scheduled departure plus `DepDelay` equals `DepTime` for every one of 624,486 departed flights, confirming that `DepDelay` is measured on the same (gate) clock. The full check (departure and arrival clock times against the computed instants) disagrees by more than 1 minute for 6 of 622,520 flights (0.001%, limit 1%); those are internally inconsistent BTS records and are flagged `clock_time_mismatch`. Separately, 35 flights have a `CRSArrTime` that disagrees with `CRSDepTime` + `CRSElapsedTime`; they are spread across many airports in both directions (not a time-zone mapping error) and are reported in `quality.json` only, because scheduled arrival is always computed from elapsed minutes.
- **Implementation note:** the conversion runs inside DuckDB by joining against per-zone tables of constant UTC offsets built with `zoneinfo` (exact, because US zones change offset only on whole hours); a randomized test checks it against `zoneinfo` directly. The `tzdata` package is pinned, and the package clears the `zoneinfo` search path on import, so the rules always come from that package and never from the host's system database (Windows has none; Linux and macOS would otherwise take theirs first).

## R4. Airport time zones

- **Decision:** use the **`airportsdata`** Python package, loaded keyed by IATA code, using its `tz` field (IANA time zone names). It is MIT-licensed and its version is pinned in `uv.lock`. Proposed as **ADR-0011**, superseding the source named in ADR-0008.
- **Rationale:** installable and versioned, so lookups are reproducible; IANA names; MIT license. OpenFlights' public copy is described by its maintainers as "a sporadically updated static snapshot."
- **Alternatives considered:** OpenFlights `airports.dat` (ODbL, sporadic updates, attribution required); computing zones from coordinates (extra dependency, no benefit).
- **Missing airports:** any BTS airport without a mapping stops the run with a list (FR-004). A small override table in config can fill gaps, with each override's source noted. **Verified (12-month run):** one airport, PBI (Palm Beach International), is absent from airportsdata 20261123; the run stopped as designed, and PBI is mapped to `America/New_York` in `[timezones.overrides]` with its source.

## R5. Confidence interval for the difference in feasibility rates

- **Decision:** a **paired day-level bootstrap**:
  - Resample service dates (the union of dates on which either itinerary has an outcome) with replacement, 10,000 times, using a fixed seed.
  - For each resample, compute each itinerary's feasibility rate on the dates it has outcomes, and take the difference.
  - The 95% interval is the 2.5th to 97.5th percentile of the differences.
- **Rationale:** resampling whole dates keeps the correlation between two itineraries flying on the same day (shared weather and congestion), as the spec requires. It also handles dates where only one itinerary operated. A fixed seed makes it reproducible.
- **Alternatives considered:** Newcombe's interval for independent proportions (ignores pairing; conservative only when correlation is positive); McNemar-style paired intervals (require both itineraries on every date).
- **Testing:** the bootstrap function is tested on synthetic data with a known difference, and against a closed-form interval in a case without correlation.

## R6. Building itineraries efficiently and handling schedule changes

- **Decision:** pair at the **schedule-pattern level**, then compute daily outcomes only where needed:
  1. A *flight pattern* is marketing airline + flight number + origin + destination. Its recurrence is the share of days in the period on which it was scheduled (cancelled flights count).
  2. Patterns meeting the recurrence threshold are paired through each hub by marketing airline (or partner pair) when their **median** scheduled layover falls within the limits.
  3. On each day, the outbound instance is the one whose scheduled departure falls within the layover limits after that day's inbound scheduled arrival. Days where no such instance exists are counted as "not connecting that day" and excluded from the sample. In sensitivity scenarios the window uses the scenario's minimum connection time, so a stricter minimum also removes days whose scheduled layover falls below it (those connections would not be sold); this changes the day sample as well as the threshold, and is disclosed in the methodology.
  4. Daily outcomes are computed only for itineraries in the selected origin/destination pairs. Hub eligibility and pair ranking use pattern-level counts only.
- **Rationale:** joining every flight with every flight at a hub every day is far larger than needed. Pattern pairing is small, and the daily check handles schedule changes and next-day departures correctly.
- **Schedule changes:** if a flight number's times change during the year, its median layover is used for qualification, and daily matching decides which days actually connect. The share of excluded days is reported per itinerary.

## R7. Notebook tool

- **Decision:** **marimo**.
- **Rationale:** notebooks are stored as plain Python files, so diffs are clean and reviewable; they can run as scripts and export to HTML for the report; execution order is fixed, so results can't depend on cell order.
- **Alternatives considered:** Jupyter (JSON files with embedded outputs, noisy diffs, cells can run out of order).

## R8. Determinism

- **Decision:** every output table has an explicit sort order (listed in [contracts/outputs.md](contracts/outputs.md)); random processes use one seed from config; the run manifest records config hash, source file checksums, package versions and a hash of each output table. The determinism test runs the pipeline twice on fixtures and compares output hashes. Floating-point sums in DuckDB can vary in the last digits with thread scheduling, so rates and shares are computed from integer counts (a division of two integers, done once), percentiles are taken over integer minutes, and every float column is rounded to 6 decimal places before it is written. Parquet files are written with fixed writer settings (compression, row-group size, no creation timestamp) so identical tables give identical bytes.
- **Rationale:** required by FR-033 and SC-001.

## R9. Configuration format

- **Decision:** one TOML file (`config/phase0.toml`), read with Python's built-in `tomllib` and validated by Pydantic models. Every default in the spec appears explicitly in the file.
- **Rationale:** readable, comment-friendly, no extra dependency, and validation gives clear errors.

## R10. Sold routings from DB1B (amendment 1, ADR-0013)

- **Decision:** use the BTS **DB1B Market** table, which is published as pre-zipped quarterly files: `https://www.transtats.bts.gov/PREZIP/Origin_and_Destination_Survey_DB1BMarket_{YYYY}_{Q}.zip`. Each file is about 110 MB zipped and 2.1 GB unzipped.
  - **Fields:** a directional market row has `AirportGroup` (the routing, for example `LGA:ATL:LAX`), `TkCarrierGroup` (the selling airline per leg, for example `DL:DL` or `AA:AS`), `MktCoupons` (number of legs) and `Passengers` (sampled passengers).
  - **Routing:** a row with `MktCoupons = 2` is a trip with one connection. Splitting `AirportGroup` and `TkCarrierGroup` gives origin, hub, destination and the two selling airlines.
  - **Aggregation:** sold routings are aggregated per quarter and summed over the period.
  - **Unknown airlines:** legs with selling airline `--` (not recorded) are not counted, and their passenger share is reported.
  - **Checksums:** the files are pinned per quarter, as for the on-time files.
  - **Disk space:** each quarter's CSV is extracted, aggregated with DuckDB and then deleted, so only the zips and the small aggregate stay on disk.
- **Verified (2026-11-24, quarter 2025-2):**
  - The file holds 8.45 million market rows, of which 3.47 million (3.83 million passengers) have 2 coupons.
  - Extraction takes about 5 seconds and aggregation about 2 seconds.
  - Example routings: `LGA:ATL:LAX DL:DL` has 117 sampled passengers and `LGA:ORD:LAX UA:UA` has 207. The detour `DTW:MCO:ATL` on DL doesn't appear among the top DTW–ATL routings.
  - Partner tickets appear as mixed pairs such as `AA:AS`.
- **Latest available quarter:** 2025-2, both pre-zipped and in the TranStats form ("Latest Available Data: June 2025"). This sets the analysis period (R11).
- **Alternatives considered:**
  - The DB1B Coupon table: the same routing information split across rows, at 255 MB zipped per quarter.
  - A travel-time cap relative to the nonstop: the threshold is arbitrary, and it doesn't measure whether anyone buys the routing.

## R11. One period for all sources (amendment 1, option A)

- **Decision:** on-time, T-100 and DB1B all cover **July 2024 to June 2025**: quarters 2024-3 to 2025-2. The period must start and end on quarter boundaries.
- **Rationale:** DB1B is the source published latest. Aligning the periods means every number describes the same months, and it removes the earlier one-month T-100 offset.
- **Consequence:** the on-time checksums pinned for October 2025 to September 2026 no longer apply. The new months are downloaded and pinned on the first run.

## R12. Connection-level recurrence and order of the itinerary rules (amendment 1)

- **Decision:** itineraries are built in this order:
  1. Candidate pattern pairs: airline-compatible, with each pattern scheduled on at least the recurrence threshold share of days. Each pattern meeting the threshold on its own is a necessary condition for the pair to meet it, so this filter loses nothing.
  2. Median layover within limits (FR-015).
  3. Sold routing, joined against the aggregated DB1B routings (FR-013a).
  4. Connection-level recurrence (FR-016). This uses the same daily matching as the feasibility stage, but on scheduled times only. The count is days with a scheduled outbound flight inside the layover window after that day's scheduled inbound arrival, divided by days in the period.

  The candidates removed at each step are counted for every selected origin/destination pair (FR-018a).
- **Rationale:** the DB1B join is cheap and removes most candidates, so the daily matching (step 4) only runs on routings that are actually sold.
- **Sensitivity:** in each scenario, the minimum connection time moves the matching window and the recurrence threshold applies to the connection share. So both kinds of scenario can now change which itineraries qualify. Rates still depend only on the minimum connection time and the cutoff, so robustness is reported as distinct (minimum connection time, cutoff) settings compared.
