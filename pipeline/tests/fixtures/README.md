# Reference fixtures

Small committed samples used by the tests. Expected results in `expected/` are computed by
hand from the cases below, never by the pipeline code.

## `ontime_sample.csv`

Built by `make_ontime_sample.py` in the real BTS Marketing Carrier format: the same column
names (including `Operating_Airline ` with its trailing space and the trailing empty column),
zero-padded `HHMM` times, `x.00` numbers, and `2400` for actual midnight. Extra columns
(`Year`, `Tail_Number`, `FixtureCase`) must be ignored by the pipeline. `FixtureCase` names
each row.

Hub: ORD. Main period for itinerary tests: 2026-01-05 to 2026-01-14 (10 days, d1–d10).

| Case | Rows | What it covers |
|---|---|---|
| Itinerary 1 | AA3100 CMH→ORD (operated by MQ) + AA1500 ORD→SAN, 08:00 ET / 09:50 CT | Same marketing airline, 90 min layover, regional operator |
| d1 | outbound +5 | Feasible, slack 95 |
| d2 | inbound +50 (NAS delay) | Insufficient time, slack 40; NAS delay is not weather |
| d3 | inbound +40, 85 min block | Feasible at the boundary, slack 45 = 30 + 15 |
| d4 | inbound cancelled, code B | Cancelled; weather-affected |
| d5 | outbound cancelled, code A | Cancelled |
| d6 | inbound diverted | Diverted |
| d7 | inbound operated with missing actual times | Excluded, quality |
| d8 | inbound +120 (weather delay) | Negative slack (−28) → insufficient time; weather-affected |
| d9 | outbound row duplicated identically | One copy kept; feasible, slack 90 |
| d10 | two conflicting inbound copies (+0 and +30) | Both excluded; day excluded, quality |
| Partner | AS700 / AS702 ORD→SEA at 09:30 / 09:00 | AA+AS partner: 70 min included; 40 min below the 45 min partner minimum |
| Layover limits | AA1502 / AA1504 / AA1506 ORD→SAN at 08:40 / 12:30 / 12:20 | 20 min (too short), 250 min (too long), 240 min (boundary, included) |
| Recurrence | AA1508 on 5/10 days; AA1510 on 6/10 days with 2 cancelled | 50% excluded at 60%; cancellations count as scheduled |
| Same operator | DL5000 CMH→ORD and UA6000 ORD→SAN, both operated by OO | Different marketing airlines, not partners: never paired |
| Connection-level recurrence | UA7000 CMH→ORD 09:00 ET + UA7001 ORD→DEN, both daily; UA7001 leaves 10:20 CT on odd days, 14:30 CT on even days | Layover 60 min at the pattern level and sold, but connects on 5 of 10 days: excluded at 60% |
| Midnight | AA2200 CMH→ORD 22:00 ET + AA2300 ORD→PHX 00:30 CT (next day) | Layover across local midnight; d2 inbound arrives at 00:00 local (`2400`); last inbound day has no next-day outbound → not connecting |
| Daylight saving | WN101/102 on 2026-03-08; WN201/202 on 2025-11-02 | True slack 30 (spring) and 140 (fall) vs naive local 90 and 80 |
| `2400` / `0000` | WN301 PHX→SAN `2400` on 01-07; WN302 `0000` on 01-08 | Same instant, 2026-01-08 07:00 UTC |
| Clock mismatch | WN401 with `ArrTime` 15 min off | Flagged `clock_time_mismatch` |

Time zones crossed: Eastern → Central (CMH→ORD), Central → Pacific (ORD→SAN/SEA), Central →
Mountain without DST (ORD→PHX).

## `db1b_sample.csv`

Built by `make_db1b_sample.py` with the real DB1B Market header (41 columns and the trailing
empty column). Sampled passengers per case:

| Case | Coupons | Routing | Selling airlines | Passengers | What it covers |
|---|---|---|---|---|---|
| san_q1, san_q4 | 2 | CMH:ORD:SAN | AA:AA | 20 (2026-1) + 15 (2025-4) | One routing over two quarters: 35, above the minimum of 30 |
| sea_partner | 2 | CMH:ORD:SEA | AA:AS | 40 | Partner ticket matched to the AA+AS itinerary |
| den_below_min | 2 | CMH:ORD:DEN | AA:AA | 12 | Below the minimum: AA3100+AA1510 excluded as not sold |
| phx | 2 | CMH:ORD:PHX | AA:AA | 50 | Sold: the midnight itinerary qualifies |
| ua_den | 2 | CMH:ORD:DEN | UA:UA | 60 | Sold: UA7000+UA7001 is excluded only by connection-level recurrence |
| dl_ua | 2 | CMH:ORD:SAN | DL:UA | 30 | Sold, but DL and UA are not partners: never an itinerary |
| legacy_code | 2 | CMH:ORD:SAN | US:AA | 4 | Joins AA:AA only with `carrier_map = {US = "AA"}` |
| unknown_out, unknown_in | 2 | CMH:ORD:SAN | AA:--, --:AA | 5, 3 | Not counted; 8 of 239 two-coupon passengers (3.3473%) |
| one_coupon | 1 | CMH:ORD | AA | 100 | Ignored: a nonstop trip |
| three_coupons | 3 | CMH:ORD:DEN:SAN | AA:AA:AA | 50 | Ignored: would otherwise add to CMH:ORD:DEN |

## `t100_sample.csv`

T-100 segment rows in the form-download header order, including two rows for the same airport,
carrier and month (summed), a zero, and a month outside a one-month test period.

## `expected/`

- `timeconv.json`: UTC instants per case.
- `quality.json`: data-quality flags and counts.
- `itineraries.json`: patterns, itineraries and per-pair exclusion counts for hub ORD over the
  10-day period, with the sold routings of `db1b_sample.csv`.
- `sold_routings.json`: sold routings and the unknown-airline share from `db1b_sample.csv`.
- `daily_outcomes.json`: per-day outcomes and summary results for itinerary 1 and the
  midnight itinerary; slack across both daylight-saving changes.
