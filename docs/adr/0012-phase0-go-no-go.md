# ADR-0012: Phase 0 go/no-go: GO

- **Status:** Accepted (2026-11-24, by the owner, after independent review rounds 6–10 of amendment 1).
- **Date:** 2026-11-24
- **Evidence:** [reports/phase0/summary.md](../../reports/phase0/summary.md) (full results), [summary.json](../../reports/phase0/summary.json) (every example), [manifest.json](../../reports/phase0/manifest.json); method in [docs/methodology.md](../methodology.md); feature spec [specs/001-bts-connection-experiment](../../specs/001-bts-connection-experiment/spec.md); independent review [review.md](../../specs/001-bts-connection-experiment/review.md); itinerary rules in [ADR-0004](0004-itinerary-definition.md) and [ADR-0013](0013-sold-routings-and-connection-recurrence.md). The results are reproduced from the git tag `phase0-final` (`flight-pipeline verify --config ../config/phase0.toml` on that tag); later code follows ADR-0014.

## Context

The project's central claim is that itineraries a traveler would consider equivalent can differ meaningfully in how often their connection works. Phase 0 tested that claim on 12 months of public BTS data before any product work. One period, July 2024 to June 2025, covers every source:

- on-time data: 7,671,287 scheduled flights;
- DB1B Market: quarters 2024-3 to 2025-2, used to keep only routings people actually buy;
- T-100 passenger data, used for the hub score.

A first run on October 2025 to September 2026 met the go criterion on paper. Independent review (rounds 4–5) found that most of its examples were detours nobody buys, or itineraries whose two flights rarely connected. Spec amendment 1 (ADR-0013) therefore added two rules: the routing must be sold in DB1B (at least 30 sampled passengers) and the two flights must connect on at least 60% of days. DB1B's publication lag moved the period to July 2024 to June 2025. This ADR records the result of the rerun.

The go criterion was fixed in advance (spec FR-030): at least 3 showcase examples spread across at least 2 hubs. A showcase example is a pair of comparable itineraries that meets all of the following:

- the same origin and destination, scheduled travel time within 60 minutes of each other, and departure within 3 hours of each other;
- at least 30 paired days for each itinerary, at least 30 of them on the same dates;
- no reversal of the pair's order in any sensitivity scenario where both itineraries qualify;
- connection feasibility that differs by at least 10 percentage points, with a 95% confidence interval (paired day-level bootstrap) that excludes zero.

## Decision

**GO.** Every itinerary in the analysis is on a sold routing, and its flights connect on most days, and the criterion is met with a wide margin:

| Criterion | Required | Observed | Result |
|---|---|---|---|
| Showcase examples | at least 3 | 81, in 9 origin/destination pairs | met |
| Hubs spanned by the examples | at least 2 | 5 (ATL, DEN, DFW, LAX, ORD) | met |

The base still holds after the stricter readings. Every count below is produced by the pipeline (summary.md, "Showcase examples" and "Breakdown of the showcase examples"; `showcase_breakdown` in summary.json) and checked by `verify`. Scheduled layover and travel time are medians of the daily scheduled values on the days the two flights connect.

- **Without tight layovers.** In 11 examples the lower itinerary is scheduled with less than its own feasibility threshold (minimum connection time plus boarding cutoff), so its gap is partly built into the schedule. The other 70 examples remain, in all 9 pairs and across all 5 hubs.
- **Robustness.** 58 examples were compared at all 9 settings of minimum connection time and boarding cutoff and never reversed. The other 23 were compared at 6 and never reversed there, but none of them was checked at a 45-minute minimum connection time. For the 11 tight examples the lower itinerary's layover is below 45 minutes, so it doesn't qualify at that setting. For the other 12, at a 45-minute minimum one of the two itineraries no longer connects on enough days. 120 of the 541 comparable pairs reverse under some setting and are excluded.

The examples are concentrated: MCO-LGA has 37, and the three Delta markets through ATL (MCO-LGA, LGA-MCO, MCO-LAX) have 64 between them. Many are two Delta itineraries through ATL that differ only in their flights. Their sold-routing evidence is also thin: DB1B counts passengers per routing, not per flight, and the Delta MCO-ATL-LGA routing has 44 sampled passengers for the year (about 440 travelers) shared by its 36 qualifying itineraries; LGA-ATL-MCO has 64 over 33 (summary.md, "Sold passengers on routing"). That is a fair comparison, because a traveler choosing among them sees the same airline, hub and similar times, but the 19 cross-hub examples (for example EWR-MKE through ORD against ATL) are the stronger showcase.

Proceed to Phase 1 (`showcase-data-pipeline`) with the consequences below.

### Hub selection and rationale

Seven hubs were selected by score from the 30 busiest airports, with no swaps: **ATL, DEN, ORD, LAX, DFW, PHX and SFO**. The score weights airline count, scheduled departures and passengers boarded equally; eligibility counts only sold, regularly connecting itineraries. Every major network (AA, DL, UA, WN, AS) has a hub, and the seasonal and median weather constraints hold. That coverage is formal, though: the itineraries themselves come almost entirely from Delta and United. Southwest sells 750,552 sampled passengers on same-airline routings through these hubs but has no itinerary, and American has 2,197 itineraries against Delta's 35,058 (summary.md, "Airlines covered"). Itineraries are identified by flight number, each flight must recur on at least 60% of days, and Southwest reassigns flight numbers often. The candidate table, with seasonal weather shares, is in the summary.

### Strongest example per pair without a tight layover (default assumptions)

| Pair | Higher | Lower | Difference (95% CI) | Settings compared | Shared dates |
|---|---|---|---|---|---|
| EWR-MKE | EWR-ORD-MKE UA661+UA5262: 94% of 233 days | EWR-ATL-MKE DL2340+DL1268: 53% of 225 days | +40 points (+33 to +47) | 9 of 9 | 137 |
| MCO-LGA | MCO-ATL-LGA DL2204+DL460: 93% of 336 days | MCO-ATL-LGA DL664+DL433: 66% of 265 days | +28 points (+22 to +34) | 9 of 9 | 243 |
| ATL-SFO | ATL-LAX-SFO DL500+DL2986: 85% of 229 days | ATL-DFW-SFO AA2403+AA446: 64% of 228 days | +22 points (+14 to +29) | 9 of 9 | 178 |
| ATL-SEA | ATL-ORD-SEA UA516+UA2211: 97% of 273 days | ATL-LAX-SEA DL301+DL1551: 76% of 231 days | +21 points (+16 to +27) | 9 of 9 | 160 |
| BNA-DEN | BNA-ATL-DEN DL3159+DL746: 95% of 329 days | BNA-DFW-DEN AA1100+AA2235: 75% of 220 days | +20 points (+14 to +27) | 9 of 9 | 187 |
| LGA-MCO | LGA-ATL-MCO DL994+DL1497: 93% of 314 days | LGA-ATL-MCO DL988+DL1497: 72% of 289 days | +20 points (+15 to +26) | 6 of 9 | 252 |
| MCO-LAX | MCO-ATL-LAX DL1446+DL501: 96% of 359 days | MCO-ATL-LAX DL1505+DL673: 76% of 226 days | +20 points (+14 to +26) | 9 of 9 | 220 |
| SAN-IAD | SAN-DEN-IAD UA2476+UA347: 93% of 263 days | SAN-LAX-IAD UA4723+UA1140: 78% of 225 days | +15 points (+9 to +22) | 6 of 9 | 166 |
| LAX-IAD | LAX-ATL-IAD DL395+DL2549: 89% of 327 days | LAX-ATL-IAD DL715+DL2549: 76% of 227 days | +13 points (+7 to +19) | 6 of 9 | 191 |

The summary shows the strongest example per pair including tight ones; summary.json lists every example.

## Consequences

**Required for Phase 1:**
- **Show the scheduled layover beside every feasibility figure**, and flag layovers shorter than minimum connection time plus boarding cutoff. They explain part of the gap in 11 examples.
- **Report robustness as settings compared**, naming the settings not compared, as the Phase 0 report now does.
- **Disclose how much longer than the nonstop a routing is.** Sold routings can still be slow: in 66 of 81 examples the slower itinerary takes more than 1.5 times the median nonstop time (most are MCO-LGA through ATL; at most 2.9 times). Travelers do buy these trips, often for price, so they stay in. The explorer should show travel time against the nonstop so users can judge.
- **Prefer cross-hub examples for the showcase** and avoid one market dominating it.
- **Check the layover rule on daily schedules.** Rule 2 still compares the two flights' separate median times as a cheap pre-filter, so when they change schedule at different times it can exclude an itinerary that would connect (the round-7 review found 2 in the selected pairs). Phase 1 should apply the layover limits only through the daily matching.
- **Identify itineraries by schedule, not only by flight number.** Recurrence by flight number leaves out Southwest entirely and most American connections. Phase 1 should recognise a connection by airline, route and a departure-time window, or explicitly justify and disclose the exclusion.
- **Use a stricter definition of "regional origin."** The spec counts any non-hub airport as regional, so LGA, MCO and BOS count as regional. Use "outside the candidate pool", as hub eligibility already does, if the showcase is meant to feature smaller airports.

**Accepted:**
- **Each comparison is one of many.** 541 pairs were each tested at 95% with no multiple-comparison correction, and showcase pairs often share an itinerary. A single example can be a chance result; the decision rests on the number and spread of examples.
- **Samples are large.** The 235 analyzed itineraries have 219 to 365 paired days at the default assumptions (at least 183 in any scenario), well above the 30-day minimum; none has insufficient data. The sample size is always shown.
- **The period is older than the latest on-time data**, because DB1B is published about 15 months after a quarter ends (ADR-0013).
- **The results are reproducible.** `flight-pipeline verify` reran every stage and matched all committed outputs and report files byte for byte.
- **Runtime is well under the limit.** The run took 7.9 minutes excluding downloads (manifest.json, `runtime_min`), against a 30-minute limit, on a 16-core, 15 GB machine, not the 4-core reference machine in SC-008.

## Known limitations

- Airlines sometimes hold an outbound flight for connecting passengers; the data can't show this.
- Gate changes and walking distances between gates are not in the data.
- How full flights were is not considered.
- Itineraries are identified by flight number, so airlines that reassign flight numbers often are missing: Southwest has no itinerary, and American is underrepresented.
- Transfer time is assumed (the hub's minimum connection time), not measured.
- DB1B is a 10% ticket sample and names the selling airline, not the flight: every flight pair on a sold routing that meets the other rules qualifies. 2.3% of its one-connection passengers have a leg with no recorded selling airline, and 0.3% are on routings sold by airlines that aren't marketing airlines in the on-time data (mostly regional and foreign airlines, listed in the summary); neither is counted.
- Results are historical frequencies for July 2024 to June 2025, not predictions. Model calibration and holdout testing are Phase 3.
- Weather is measured only through BTS weather-attributed delays and weather cancellations.
