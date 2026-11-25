# Methodology

How the project turns public flight records into connection-feasibility numbers. This version covers the Phase 0 experiment (feature `001-bts-connection-experiment`). Later phases add to it; calibration and holdout testing are Phase 3.

Every number the project reports has a written definition, a sample size and a data period (constitution, Principle I). The definitions below are the ones the code implements; the tests that check them are named in brackets.

## Data sources

| Source | Used for | Period (Phase 0) |
|---|---|---|
| BTS **Marketing Carrier On-Time Performance** (monthly pre-zipped files) | every scheduled flight: marketing and operating airline, schedule, delays, cancellations, diversions, delay causes | July 2024 to June 2025 |
| BTS **Airline Origin and Destination Survey, DB1B Market** (quarterly pre-zipped files) | which one-connection routings are actually sold, and by which airlines (a 10% ticket sample) | quarters 2024-3 to 2025-2 |
| BTS **T-100 Domestic Segment (U.S. Carriers)** | passengers boarded per airport, for the hub score only | July 2024 to June 2025 |
| `airportsdata` (MIT) | IANA time zone of each airport | pinned package version; one override (PBI) in configuration |
| `tzdata` (Apache 2.0) | time-zone rules | pinned package version; the pipeline never reads a system time-zone database, so the same rules apply on every operating system |

All sources cover the same 12 months, in whole quarters (ADR-0013). DB1B is published about 15 months after a quarter ends, so it sets the period: July 2024 to June 2025 is the latest year for which all three sources exist.

All inputs are pinned: every monthly and quarterly file and the T-100 extract have a SHA-256 checksum in `config/phase0.toml`, and `acquire` stops when a file doesn't match. Runs from files already in place (`run --no-acquire`, `verify`) don't re-check the extracted CSVs; a changed file there shows up as changed output hashes. The T-100 data is downloaded through the TranStats form by script; if that fails, a manual download is accepted only if it matches the pinned checksum.

## From records to UTC instants

BTS gives local clock times without a time zone, and actual clock times without a date. So the pipeline never infers dates from clock times. Instead (research R3, ADR-0008):

- scheduled departure = flight date + scheduled departure time, in the origin airport's zone, converted to UTC;
- scheduled arrival = scheduled departure + scheduled elapsed minutes;
- actual departure = scheduled departure + departure delay minutes;
- actual arrival = actual departure + actual elapsed minutes.

These are exact across midnight, time zones and daylight-saving changes. A check compares the computed instants with the BTS clock times; more than 1% disagreement stops the run. Over the 12-month period, 0.0015% of flights (114) disagreed and were excluded. [`test_timeconv.py`, `test_normalize.py`]

## Data quality

Each record is flagged, and only `ok` records enter any sample:

- **duplicate**: an identical copy of another record (one copy is kept);
- **conflicting duplicate**: several records for one flight that disagree (all excluded);
- **missing actual times**: an operated flight without actual times;
- **clock-time mismatch**: computed instants disagree with BTS clock times by more than one minute.

Rows whose schedule can't be converted (missing or non-positive scheduled elapsed time, or an `HHMM` time with minutes of 60 or more) are dropped and counted as `invalid_schedule`; there were 2 in 7.7 million. Every count is reported by month in `reports/phase0/quality.json`. [`test_quality.py`]

## Hub selection

Hubs are chosen from the data, not by hand (FR-006 to FR-012):

1. **Candidates**: the 30 airports with the most scheduled departures.
2. **Metrics** per candidate: airline count (marketing airlines with at least 5% of departures), scheduled departures, passengers boarded, and the weather profile. A departure is *weather-affected* when it has weather-attributed delay minutes or was cancelled for weather; National Aviation System delays are excluded because they mix weather with congestion. The weather profile is the overall share and the share per season (unknown for a season with no weather-affected departures), and the season in which it peaks.
3. **Eligibility**: at least 15 qualifying itineraries from origins outside the candidate pool.
4. **Score**: airline count, departures and passengers, each scaled to 0–1 across the candidates, with equal weights. Ties are broken by airport code.
5. **Selection**: the 7 highest-scoring eligible candidates, adjusted by swapping in the next-best candidate where needed so that every major network (AA, DL, UA, WN, AS) has a hub, at least two hubs peak in winter and two in summer, and hubs lie above and below the pool's median weather share. Each selected hub's reason is reported; unmet constraints are named. [`test_hub_metrics.py`, `test_hub_selection.py`]

## Itineraries (ADR-0004, ADR-0013)

A *flight pattern* is a marketing airline, flight number, origin and destination. Its recurrence is the share of days in the period on which it was scheduled; cancelled flights count as scheduled.

An **itinerary** pairs an inbound pattern (origin → hub) with an outbound pattern (hub → destination). The rules run in this order (research R12), and the candidates each rule removes are counted for every selected origin/destination pair and shown in the report:

1. **Candidates.** Both patterns are sold by the same marketing airline, or by a listed partner pair (AA and AS); the operating airline is never used. Each pattern is scheduled on at least 60% of days. This is necessary for rule 4, so it removes nothing rule 4 would keep.
2. **Layover.** The median scheduled layover is at least the hub's minimum connection time (30 minutes; 45 for partner connections) and at most 4 hours. Pairing works on patterns, using median local times at the hub, so it never joins every daily flight with every other.
3. **Sold routing.** DB1B shows at least 30 sampled passengers over the period on the same origin, hub and destination, with the same selling airline on each leg as the two flights' marketing airlines. A DB1B row with two coupons is a trip with exactly one connection; rows are summed over the four quarters. Legs whose selling airline is not recorded (`--`) are not counted, and their share of passengers is reported. Selling airlines that are not marketing airlines in the on-time data (after the code map) are listed in the report with their passengers; their routings can never match an itinerary. A configured code map can translate DB1B airline codes to the on-time data's marketing codes; it is empty for Phase 0. This rule removes routings nobody buys, such as long detours through a hub in the wrong direction.
4. **Connection-level recurrence.** The two flights connect on at least 60% of days in the period: on each day the inbound flight is scheduled, an outbound flight is scheduled within the layover limits after the inbound's scheduled arrival (the same daily matching as the feasibility stage below, on schedules only; cancelled flights count as scheduled). Two flights can each run every day yet connect only on some days, when one of them changes its time; such itineraries are removed.

Each itinerary records its share of connecting days (`connect_share`) and its sampled DB1B passengers (`sold_passengers`). Its scheduled layover and travel time are the medians of the daily scheduled values (UTC) on the days the two flights connect, so they describe the itinerary as flown even when a flight changes schedule during the year. Rule 2 uses the two flights' separate median times as a cheap pre-filter; when the flights change schedule at different times it can exclude an itinerary that would connect. DB1B identifies the selling airline per leg, not the flight number, so all flight pairs on a sold routing that meet the other rules qualify. Hub eligibility uses the same rules. [`test_itineraries.py`, `test_db1b.py`]

## Connection feasibility (ADR-0005)

For each itinerary and each day its inbound flight was scheduled, the pipeline finds the outbound flight scheduled to leave within the layover limits after that day's inbound arrival, which can be on the next calendar day. Then:

- a day with no such outbound flight is excluded as *not connecting*;
- a day where either leg failed a quality check is excluded as *data quality*;
- otherwise the day is **cancelled** (either leg), else **diverted** (either leg), else **feasible** when the raw slack is at least the boarding cutoff (15 minutes) plus the minimum connection time, else **insufficient time**.

**Raw slack** is the outbound flight's actual gate departure minus the inbound flight's actual gate arrival, from UTC instants, for the same connection day. Per-leg delay distributions are never combined as if independent.

**Connection feasibility** of an itinerary is the share of paired days that were feasible. An itinerary qualifies when its scheduled layover reaches the minimum connection time, but a day is feasible only when the actual slack also covers the boarding cutoff. So an itinerary scheduled with less than minimum connection time plus boarding cutoff (for example 31 minutes against 30 + 15) is feasible only on days when the inbound flight arrives early or the outbound leaves late; the report flags these itineraries next to every showcase example. With fewer than 30 paired days the itinerary shows "insufficient data" and no rate. Each result also reports the failure counts, the excluded days by reason, and slack percentiles (p10, p50, p90, using the "lower" rule, so every value is an observed minute). [`test_daily_outcomes.py`, `test_itinerary_results.py`]

This measures **connection feasibility**, not what happened to travelers: the data has no passenger records.

## Origin/destination pairs and comparability

Two itineraries are **comparable** when they share an origin and destination, their scheduled travel times differ by at most 60 minutes, and their scheduled departures from the origin are within 3 hours of each other (local time of day). Price is out of scope, so similarity is defined by time.

The 15 analyzed origin/destination pairs are chosen from the data: pairs with at least two qualifying itineraries, ranked by their number of comparable pairs, with at least half having a regional (non-hub) origin and at most three per main hub. [`test_comparability.py`, `test_od_selection.py`]

## Sensitivity (FR-027, FR-028)

Every analyzed itinerary is re-evaluated under 27 scenarios: minimum connection time 20, 30 or 45 minutes; boarding cutoff 10, 15 or 20 minutes; recurrence threshold 50%, 60% or 75%. Hub and pair selection stay fixed. Each scenario moves every minimum connection time by the same amount, so partner connections use 35, 45 and 60 minutes (the default minimum plus the 15-minute partner premium), and any per-hub minimum moves the same way. Itineraries are rebuilt in each scenario with the same four rules. The minimum applies to which itineraries qualify (layover and connecting days), to which days connect, and to the feasibility threshold. On a day whose scheduled layover is below the scenario's minimum, the connection would not be sold, so that day is excluded as not connecting rather than counted as a failure. A stricter minimum therefore changes the set of paired days as well as the threshold, and an itinerary's rate can rise under a stricter minimum when its tightest days drop out. The recurrence threshold applies to the share of connecting days, so it decides which itineraries qualify but never changes a rate. Robustness is therefore reported as **settings compared**, with the settings a showcase was not compared at named next to it: the number of distinct (minimum connection time, boarding cutoff) settings, out of 9, at which both itineraries of a pair had sufficient data in some recurrence scenario (`settings_compared`). A comparable pair is **assumption-sensitive** when its order by connection feasibility reverses in any scenario. Scenarios where an itinerary doesn't qualify or has insufficient data are reported, not counted as reversals; each pair also records how many of the 26 other scenarios it was compared in (`scenarios_compared`, in `summary.json`). [`test_sensitivity.py`]

## Showcase examples and the go criterion (FR-029, FR-030)

A **showcase example** is a comparable pair, both itineraries with sufficient data, observed on at least 30 of the same dates (so they were real alternatives at the same time and the interval is genuinely paired), and not assumption-sensitive, whose connection feasibility differs by at least 10 percentage points, with a 95% confidence interval for the difference that excludes zero.

The interval comes from a **paired day-level bootstrap** (research R5): the service dates on which either itinerary has an outcome are resampled with replacement 10,000 times (fixed seed), each itinerary's rate is computed on the drawn dates where it has an outcome, and the interval is the 2.5th to 97.5th percentile of the differences. Resampling whole days keeps the correlation between itineraries flying on the same day, such as shared weather. [`test_bootstrap.py`, `test_showcase.py`]

The **go criterion** is met with at least 3 showcase examples spread across at least 2 hubs. An example counts toward the hubs of both its itineraries, so one comparison of an itinerary through ORD with one through ATL spans 2 hubs. The decision is recorded in [ADR-0012](adr/0012-phase0-go-no-go.md).

## Precision

Rates are reported in whole percent and differences and confidence limits in whole percentage points: with the sample sizes here (219 to 365 paired days per analyzed itinerary at the default assumptions, at least 183 in any scenario; the minimum is 30), one day changes a rate by about 0.3 to 0.5 points, and much more for itineraries near the minimum, so decimals would claim precision the data doesn't have. Airport-level weather shares, based on 50,000 or more departures each, are shown with one decimal. Full-precision values (6 decimals) stay in `summary.json` and the Parquet tables for auditing.

## Reproducibility

One command rebuilds everything from the pinned configuration, and `verify` reruns it, compares the SHA-256 of every output with the committed `reports/phase0/manifest.json`, and compares the committed report files byte for byte. Report files are always written with LF line endings so the hashes hold on every operating system. Determinism comes from explicit sort orders, a fixed random seed, rates computed from integer counts, floats rounded to 6 decimals and fixed Parquet writer settings (research R8). [`test_determinism.py`]

## Known limitations

- Airlines sometimes hold an outbound flight for connecting passengers; the data can't show this.
- Gate changes and walking distances between gates are not in the data.
- How full flights were is not considered; a feasible connection doesn't mean a seat was available.
- Transfer time is assumed (the hub's minimum connection time), not measured.
- Results are historical frequencies for the data period, not predictions.
- Many comparisons are made (541 comparable pairs, each at 95%) with no multiple-comparison correction, so an individual example can be a chance result; the go decision rests on the number and spread of examples, and showcase pairs often share an itinerary.
- Weather is measured only through weather-attributed delays and weather cancellations.
- Sold routings come from DB1B, a 10% ticket sample. A routing sold rarely can fall below the 30-passenger minimum and be left out. DB1B identifies the selling airline per leg but not the flight, so every flight pair on a sold routing that meets the other rules qualifies, even if most passengers on that routing use other flights. DB1B fares are not used.
- The analysis period (July 2024 to June 2025) is set by DB1B's publication lag, so it is older than the latest on-time data.
- Itineraries are identified by flight number, and each flight must be scheduled on most days. Airlines that reassign flight numbers often are therefore missing: Southwest has no itinerary, and American is underrepresented. The report lists itineraries per airline next to the sold passengers through the selected hubs.
- "Regional origin" for pair selection means any airport that is not a selected hub, so large airports such as LGA count as regional. A stricter definition is a candidate change for Phase 1.
