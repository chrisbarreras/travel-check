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
- `verify --config ../config/phase1.toml` on 433b01c: "identical: 23 outputs, the published showcase and the generated types match the committed files".

## Round 2 (main...433b01c)

**Verdict:** CHANGES REQUIRED. 1 blocking, 5 should-fix, 3 nits. Automated checks all passed (ruff, format, pyright, 520 tests, `schemas --check`). The reviewer recomputed the slider rate for all 144 published itineraries and checked all 59 faster alternatives, the caps and the minimum sample.

### Findings and responses

| # | Severity | Finding | Response |
|---|---|---|---|
| 1 | BLOCKING | Two pytest tests run `npx --yes json-schema-to-typescript`, which downloads from the npm registry (constitution II: tests must not depend on the network). | **Fixed.** Both tests are marked `network`, and `addopts` deselects that marker. Run them with `pytest -m network`. CI still checks the committed files with the real generator in its `schemas --check` step, which is not a test. |
| 2 | SHOULD-FIX | Only the generator was pinned. Its prettier dependency (`^3.2.5`) floats, so the generated bytes could change with no code change. | **Fixed.** The generator now runs as `npx --package prettier@3.10.1 --package json-schema-to-typescript@15.0.4 json2ts`. That is the version the committed types were generated with, and `schemas --check` still passes. |
| 3 | SHOULD-FIX | The landing example's lower itinerary had a median layover exactly at its threshold, and 76 of its connecting days were scheduled below it, yet it counted as not tight. | **Fixed.** An itinerary is tight when its median scheduled layover is below the threshold, or when more than `[showcase] tight_day_share_max` (10%) of its connecting days were scheduled below it. The share comes from `itinerary_days.parquet`. The rule applies to the landing example, the published `tight_layover` flag and the report's breakdown. Phase 0's median-only rule is kept when the key is absent. Test: `test_tight_by_median_or_by_share_of_days_below_the_threshold`. Research R4, the methodology, the config contract and the definition text are updated. |
| 4 | SHOULD-FIX | The buffer was shown against the median layover, which hides layovers that vary by day. | **Fixed.** `buffer.scheduled_at_least_share` gives the share of operated days whose scheduled layover was at least the recommendation. `actual_layover_min` is described as the median. The definition and methodology are updated, with a test for the review's case. |
| 5 | SHOULD-FIX | The regional quota held back places for regional routes that didn't exist and produced a false "only N routes qualify" message. | **Fixed.** Places are held only up to the number of regional candidates. The message now reads "selected", and the regional shortfall is reported separately. Test: `test_regional_places_are_not_held_…`. The real data (8 regional routes) is unaffected. |
| 6 | SHOULD-FIX | No record showed `verify` passing on the final code. | **Fixed.** Each round's result now records its `verify` line (above for round 1; below for round 2). |
| 7 | NIT | A schedule straddling midnight forms two slots. | **Documented** in ADR-0014 (consequences) and the methodology, with the count on the Phase 1 data. Circular clustering is a candidate change for a later feature. |
| 8 | NIT | The Phase 1 report was titled as Phase 0's. | **Fixed.** `reports/phase1/summary.md` is titled "Phase 1 rerun: connection feasibility with schedule-slot itineraries". Phase 0's title is unchanged. |
| 9 | NIT | `connect_share` was published without its denominator. | **Fixed.** `schedule_warnings` carries `connecting_days` and `eligible_days`, checked against the share. |

### Round 2 result (rerun from 7f95b7c, 4 threads)

- The itineraries, examples, routes, comparisons and shares are unchanged from round 1. No cap shortfalls.
- Landing example: LIT-ATL-LGA:DL1238+DL1700 against LIT-ORD-LGA:UA1515+UA1800, +28 points. The lower itinerary's median layover is 50 minutes against its 45-minute threshold, and 5.8% of its connecting days were scheduled below the threshold. The round-1 landing example is now tight.
- 152.5 KB gzip in all, 7.0 KB for index and landing; runtime 25.0 minutes (thread limit 4).
- All quickstart validation scenarios pass; `schemas --check` passes.

## Round 3 (main...3a8e4b6)

**Verdict:** APPROVE. 0 blocking, 3 should-fix, 4 nits. Automated checks all passed (ruff, format, pyright, 521 tests with 2 network tests deselected, `schemas --check`). The reviewer also checked the committed data:
- Validated every committed showcase file against the models and recomputed every rate (146 entries, 0 mismatches).
- Matched every file checksum with the manifests.
- Checked the caps, monthly sums, intervals and flags.

### Findings and responses

| # | Severity | Finding | Response |
|---|---|---|---|
| 1 | SHOULD-FIX | The pipeline (DuckDB, halves away from zero) and the shared slider calculation (Python `round`, halves to even) could round a rate exactly halfway at the 7th decimal differently, for example 1 of 128 days. No current itinerary has such a count. | **Fixed.** The shared cases' rule now states halves away from zero, and two tie cases were added (1 and 77 of 128 days). `recompute` uses `rate_of_days`, which is exact integer arithmetic. An exhaustive check against DuckDB's `round` for every k/n with n ≤ 366 finds no mismatch. The monthly rate and the buffer share use the same helper. |
| 2 | SHOULD-FIX | No record that `verify` passed on the final code. | **Fixed.** A `verify` run on 3a8e4b6 found one difference: `summary.md`. The Phase 1 report title was taken from the reports directory's name, which `verify` replaces with a temporary directory. The title now comes from the configuration file's name (commit b92c92d, with a test). The final `verify` line is recorded below. |
| 3 | SHOULD-FIX | The roadmap showed superseded figures. | **Fixed.** It links to validation.md instead of repeating figures. |
| 4 | NIT | The published definitions hard-code 10% and 5 minutes, which come from the configuration. | **Guarded.** A test fails when `config/phase1.toml` and the definition texts disagree. The definitions stay static text, so the published bytes don't depend on code paths that read the configuration. |
| 5 | NIT | `tight_day_share_max` was optional. | **Fixed.** It is required, like every other value (Phase 0's configuration has no `[showcase]` section). |
| 6 | NIT | The methodology, research R2 and the data model described the bound pre-filter and the tight flag inaccurately. | **Fixed.** All three now describe what the code does. |
| 7 | NIT | ADR-0014 was amended in place. | **Kept as a dated clarification.** The amendment refines how slots are joined across schedule changes without changing the decision (schedule-slot identity), and it is dated and marked as an amendment. A superseding ADR is for a changed decision. |

### Final verification

- `verify --config ../config/phase1.toml` on 84557f0 (the round 3 fixes in ef35005, data regenerated from them): "identical: 23 outputs, the published showcase and the generated types match the committed files". ruff, format and pyright clean; 527 tests passed (2 network tests deselected); `schemas --check` up to date; all validation scenarios pass.
