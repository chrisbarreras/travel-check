# Independent reviews: 002-showcase-data-pipeline

Reviews by a new `feature-reviewer` agent each round, given only this feature directory and the base branch `main` (T052, constitution Development Workflow).

## Round 1 (main...690daa1)

**Verdict:** CHANGES REQUIRED. 3 blocking, 5 should-fix, 3 nits. Automated checks all passed (ruff, format, pyright, 510 tests, `schemas --check`).

### Findings and responses

| # | Severity | Finding | Response |
|---|---|---|---|
| 1 | BLOCKING | The connection share divided connecting days by the days the inbound slot flew, not the days in the period (ADR-0013 rule 2, data-model `eligible_days`). An itinerary connecting on 36–60% of the period's days could qualify. | **Fixed.** `eligible_days` = days in the period − end-of-period days, and a day the inbound flight isn't scheduled counts as not connecting (`itineraries.py` `_finish`). New test: an inbound slot skipping 4 of 10 days gives a share of 0.6 and is excluded at 0.7 (`test_share_counts_days_the_inbound_does_not_fly`). Methodology step 5 updated. Outputs regenerated. |
| 2 | BLOCKING | The airline cap was exceeded in the delivered showcase (American 54% against 50%), and the airline and hub shares were only in a git-ignored file (FR-008). | **Fixed.** After the additive balancing, curation applies repair moves while they lower the total excess over the caps: add one comparison, or remove one or two (each route keeps one). Two at once are needed when one airline is over its cap while others are at theirs. Then additions resume within the caps (`curation.py` `_repair`; test `test_repair_removes_pairs_…`). On the real data every cap now holds (see Round 1 result). `index.json` carries `balance` (caps, airline and hub shares, cross-hub share, shortfalls). The report has a "Showcase curation" section. A shortfall is still reported if no move can meet a cap (research R4, which the plan approved); FR-008's caps are met whenever they can be. |
| 3 | BLOCKING | Faster alternatives published `rate_this` and `rate_other` without their sample size (Principle I). 18 of 54 name an itinerary outside the route file. | **Fixed.** Both are `Rate` objects carrying status, rate, paired days, count and definition, as connecting options already did. Schema and types regenerated. `schema_version` stays 1.0.0: nothing consumes the contract yet, so the first version merged is the first release. |
| 4 | SHOULD-FIX | The buffer's lower discrete quantile can cover fewer than 95% of days (28 of 30). | **Fixed.** The buffer is the smallest needed layover covering at least the share: position ceil(share × n). Property test: coverage ≥ share for random inputs. The review's 30-day case is a test. Methodology and research R10 updated. |
| 5 | SHOULD-FIX | Coverage reasons were wrong for airlines below the sold-passenger minimum (NZ, AC, AM). | **Fixed.** An airline with sold passengers but no routing at the 30-passenger minimum says so. One with itineraries in the analysis but none on the curated routes says that (fixed before this review). The remaining reason reads "none of its schedules recur and connect regularly within the layover limits", which covers slot recurrence, the bound filter and connection recurrence. |
| 6 | SHOULD-FIX | The published `paired_days` definition said "flown", but paired days include cancelled and diverted days. | **Fixed.** The text now matches the methodology. |
| 7 | SHOULD-FIX | The bound pre-filter's property test exercised `bounds_allow`, not the production SQL. | **Fixed.** The SQL is now `bounds_table`, and a Hypothesis test checks that it keeps exactly what `bounds_allow` keeps. Together with the existing losslessness test of `bounds_allow`, this covers the production path. |
| 8 | SHOULD-FIX | The manifests didn't show that the SC-008 time was measured with a thread limit. | **Fixed.** `run.machine.thread_limit` records `FLIGHT_PIPELINE_THREADS`. validation.md and research R16 state that 4 threads on the 16-core development machine stand in for the 4-core reference machine. |
| 9 | NIT | `landing.json` didn't include insight-referenced itineraries, as the contract said it would. | **Contract changed** to match the code and the route-file rule: insight entries carry every figure shown, so the referenced itineraries aren't needed. |
| 10 | NIT | The disruption-note loader ignored unknown keys and accepted an empty `id`. | **Fixed.** Unknown keys, missing required keys and an empty `id` are rejected, with tests. |
| 11 | NIT | The arrival-minute lookup didn't join on destination and fell back to midnight. | **Fixed.** It joins on destination and raises on a missing slot. |

### Round 1 result (rerun from 104fe1c, 4 threads)

- 146,444 itineraries through the hubs (164,819 before the connection-share fix); 449 showcase examples in 15 pairs.
- 12 routes and 122 showcase comparisons; airline shares American, Delta and United 50% each; largest hub ATL 48%; largest route 12.3%; cross-hub 75%; no shortfalls.
- Southwest: 117 itineraries in the analysis (0 in Phase 0), none on the curated routes, stated in the coverage note.
- 150.8 KB gzip in all, 6.9 KB for index and landing; runtime 24.1 minutes (thread limit 4, recorded in the manifests).
- All quickstart validation scenarios pass (validation.md).
