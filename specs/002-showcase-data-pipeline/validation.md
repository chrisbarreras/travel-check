# Validation: Showcase Data Pipeline

Results of the [quickstart](quickstart.md) validation scenarios (T051) on the pinned real data, July 2024 – June 2025, `config/phase1.toml`. Run on 2026-11-26, from commit `d0d7d63`, with `FLIGHT_PIPELINE_THREADS=4`.

## Run

| Stage | Result |
|---|---|
| prepare | 7,671,287 flights (114 flagged), 279,924 sold routings |
| select-hubs | 7 hubs: ATL, DEN, DFW, LAS, LAX, ORD, PHX |
| build | 164,819 itineraries through the hubs; 15 origin/destination pairs selected (8 regional) |
| analyze | 679 itineraries, 27 scenarios, 3,922 comparable pairs, 541 showcase examples |
| curate | 12 routes, 104 showcase comparisons (83% cross-hub); 1 shortfall: American supplies 54% of comparisons, above the 50% airline cap |
| insights | 581 itineraries: 249 with a faster alternative, 189 with a better connecting option, 560 with a schedule change |
| publish | 12 route files, 144 itineraries; 145.8 KB gzip in all, 6.6 KB for `index.json` and `landing.json` |
| runtime | 28.3 minutes excluding downloads, 4 threads (limit 30, SC-008) |

## Scenarios

| Scenario | Result |
|---|---|
| Renumbered flights form one itinerary (US1) | Pass: unit tests on the slot fixture |
| Layover by daily matching only (US1) | Pass: unit tests on the schedule-change fixture |
| Airline coverage (SC-001) | Pass. Showcase itineraries by inbound airline: American 54, United 54, Delta 33, Southwest 3; Alaska none on the curated routes (45 in the analysis), with that reason stated. In the analysis Southwest has 537 itineraries (0 in Phase 0). |
| Balance (SC-002) | Pass: the largest route supplies 14.4% of the comparisons (limit one third); 82.7% cross-hub (minimum half) |
| Slider data reproduces the rate (SC-004) | Pass: the rate recomputed from every published itinerary's daily series at its transfer time equals the published rate and counts, for all 144 itineraries; shared test cases pass in Python |
| Faster alternatives (SC-005) | Pass: all 54 listed alternatives have a lower bound of at least −2 points, a saving of at least 15 minutes and at least 30 shared days |
| Size (SC-007) | Pass: 145.8 KB gzip in all (budget 2 MB); `index.json` plus `landing.json` 6.6 KB (budget 150 KB); `landing.json` holds the landing comparison and both itineraries |
| Reproducibility (SC-006) | Pass: `verify` reruns every stage and finds the published showcase, the reports and the generated types identical; `schemas --check` passes |

## Observations

- **Southwest** has few itineraries even with schedule-slot identity: 5% of its slots are scheduled on at least 60% of days, against 35–44% for American, Delta and United, because its departure times vary by day of week and season. The report and methodology state this. Lowering the recurrence threshold, or recognising day-of-week patterns, would add Southwest itineraries; that is a methodology change for a later feature.
- **Schedule changes** are frequent: 560 of 581 itineraries have at least one (a shift of 10 minutes or more lasting 7 days or more on either leg), typically 3–8 a year, mostly 10–20 minutes. They are real timetable adjustments; the explorer shows them as warnings with the connection share.
- **Airline balance**: American supplies 54% of showcase comparisons. A comparison counts for both itineraries' airlines, and each route's strongest comparison is kept, so the cap could not be met; the shortfall is reported in `curation.json` and the summary.
