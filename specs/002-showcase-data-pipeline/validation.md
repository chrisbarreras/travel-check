# Validation: Showcase Data Pipeline

Results of the [quickstart](quickstart.md) validation scenarios (T051) on the pinned real data, July 2024 – June 2025, `config/phase1.toml`. Run on 2026-11-26 from commit `7f95b7c` (after review round 2), with `FLIGHT_PIPELINE_THREADS=4`.

## Run

| Stage | Result |
|---|---|
| prepare | 7,671,287 flights (114 flagged), 279,924 sold routings |
| select-hubs | 7 hubs: ATL, DEN, DFW, LAS, LAX, ORD, PHX |
| build | 146,444 itineraries through the hubs; 15 origin/destination pairs selected (8 regional) |
| analyze | 593 itineraries, 27 scenarios, 2,973 comparable pairs, 449 showcase examples |
| curate | 12 routes, 122 showcase comparisons (75% cross-hub); American, Delta and United each supply 50% (cap 50%); no shortfalls; landing LIT-ATL-LGA (DL) against LIT-ORD-LGA (UA), +28 points, the lower itinerary's median layover 50 minutes against a 45-minute threshold, 5.8% of its connecting days scheduled below it |
| insights | 487 itineraries: 196 with a faster alternative, 156 with a better connecting option, 470 with a schedule change |
| publish | 12 route files, 144 itineraries; 152.5 KB gzip in all, 7.0 KB for `index.json` and `landing.json` |
| runtime | 25.0 minutes excluding downloads (limit 30, SC-008) |

The runtime was measured on the 16-core development machine with DuckDB and the bootstrap workers limited to 4 (`FLIGHT_PIPELINE_THREADS=4`, recorded as `run.machine.thread_limit` in both manifests). This stands in for the 4-core reference machine. It is a proxy, not a measurement on that machine.

## Scenarios

| Scenario | Result |
|---|---|
| Renumbered flights form one itinerary (US1) | Pass: unit tests on the slot fixture |
| Layover by daily matching only (US1) | Pass: unit tests on the schedule-change fixture |
| Airline coverage (SC-001) | Pass. Showcase itineraries by inbound airline: American 51, United 50, Delta 43. Southwest (117 in the analysis, 0 in Phase 0) and Alaska (28) have none on the curated routes, with that stated. |
| Balance (SC-002) | Pass: the largest route supplies 12.3% of the comparisons (limit one third); 74.6% cross-hub (minimum half); every airline and hub cap holds |
| Slider data reproduces the rate (SC-004) | Pass: for all 144 itineraries, the rate recomputed from the published daily series at the itinerary's transfer time equals the published rate and counts. The shared test cases pass in Python. |
| Faster alternatives (SC-005) | Pass: all 59 listed alternatives have a lower bound of at least −2 points, a saving of at least 15 minutes and at least 30 shared days; each rate carries its sample |
| Size (SC-007) | Pass: 152.5 KB gzip in all (budget 2 MB); `index.json` plus `landing.json` 7.0 KB (budget 150 KB); `landing.json` holds the landing comparison and both itineraries |
| Reproducibility (SC-006) | Pass: `verify` and `schemas --check` (see review.md for the final run) |

## Observations

- **Southwest** has few itineraries even with schedule-slot identity. 5% of its slots are scheduled on at least 60% of days, against 35–44% for American, Delta and United, because its departure times vary by day of week and season. The report and methodology say so. Lowering the recurrence threshold, or recognising day-of-week patterns, would add Southwest itineraries. That would be a methodology change for a later feature.
- **Schedule changes** are frequent: 470 of 487 itineraries have at least one. A change is a shift of 10 minutes or more, lasting at least 7 days, on either leg. Most are 10–20 minutes, typically 3–8 a year. They are real timetable adjustments, and the explorer shows them as warnings next to the connection share.
