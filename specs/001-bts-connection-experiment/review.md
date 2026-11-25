# Independent review: 001-bts-connection-experiment

Reviews by new `feature-reviewer` agents with no prior context (constitution, Development Workflow). Each round's report is kept verbatim; the implementer's responses follow it.

---

## Round 1 (2026-11-24): CHANGES REQUIRED

> Review: 001-bts-connection-experiment (main...26db256 + uncommitted working tree)
>
> **Verdict:** CHANGES REQUIRED
>
> Two blocking issues: the committed report hashes are only reproducible on Windows (CRLF), and the sensitivity analysis never varies the minimum connection time for partner itineraries even though the methodology says every itinerary is re-evaluated at 20/30/45 min. Everything else is solid. Note that nothing for this feature is committed yet; the whole change lives in the working tree, so test-first ordering (Principle II) could not be verified from history, and the constitution requires spec files to be committed together with code.
>
> **Checks run:** `pytest -q` 249 passed; `ruff check .` passed; `ruff format --check .` 56 files formatted; `pyright` 0 errors; `flight-pipeline verify` (real data, Windows) exit 0, 14 outputs identical. No TypeScript in Phase 0.
>
> 1. **[BLOCKING] Committed reports are written with CRLF line endings, so manifest hashes break under git and `verify` fails off Windows.** `stages.py:87` (`write_json`), `stages.py:581-582`, `cli.py:60` use `Path.write_text` without `newline=`. `.gitattributes` normalizes to LF, so the committed bytes no longer match `manifest.json`; on Linux/macOS `verify` exits 1 for summary.json, summary.md, quality.json (SC-001, FR-033). Fix: write with `newline="\n"`, regenerate, add a test that report files contain no `\r`.
> 2. **[BLOCKING] Minimum connection time is never varied for partner itineraries, contradicting the methodology and summary.** `sensitivity.py:48-49` replaces only `min_connection_default_min`, and `config.py:214-218` takes `max(base, min_connection_partner_min)`, so partner connections use 45 in all three scenarios (FR-027, SC-005). Example: `ATL-DFW-SEA:AA2770+AS543` is 0.948148 under mct20/30/45. 18 of 222 showcase examples involve a partner itinerary; 5 are partner-vs-partner and labelled "not assumption-sensitive" though never stress-tested on transfer time (including ADR-0012's HNL-SEA example). The same applies latently to `min_connection_by_hub`. Fix: define how partner and per-hub minimums move per scenario, test that a partner threshold changes, fix the wording.
> 3. **[SHOULD-FIX] Most showcase examples were reversal-checked in far fewer than 26 scenarios, undisclosed.** Of 222 examples only 68 were comparable in all 26 non-default scenarios; 118 in 17; 36 in only 11 (never at mct45 or rec75). Fix: report the number of compared scenarios per showcase pair and the distribution.
> 4. **[SHOULD-FIX] Itineraries whose scheduled layover is below MCT + cutoff are infeasible on every on-time day; undisclosed.** 24 of 445 analyzed itineraries; the lower-rated itinerary in 54 of 222 showcase examples (e.g. `MSP-MCO-ATL:DL2225+DL1150`, 31 min against 45). Fix: state the mechanism in methodology and ADR-0012 and report or flag it.
> 5. **[SHOULD-FIX] `verify` checks the manifest's hashes, not the committed report files, and compares the exact Python patch version.** Hand-editing summary.md/summary.json passes `verify`; a different 3.13.x gives "packages differs". Fix: also compare committed report files; pin Python or compare locked packages only.
> 6. **[SHOULD-FIX] Rates and differences shown with more precision than the samples support (Principle I).** `report.py` prints 0.1% / 0.1 points; no precision rule documented. Fix: document a rule (e.g. whole percent and whole points) and apply it.
> 7. **[NIT] flights.parquet sort order is not total.** Conflicting copies share the sort key (4 such rows), so file order and hash could vary. Fix: add `dest` and signature columns to the sort key.
> 8. **[NIT] Document claims vs evidence.** ADR-0012 says 4.7 min but manifest says 4.92; SC-008's reference machine is 4 cores but the run was on 16; methodology says "a changed file stops the run", but `run --no-acquire`/`verify` don't re-check extracted CSVs (only indirectly through output hashes).
> 9. **[NIT] Very roundabout itineraries are allowed and not listed as a limitation.** e.g. MSP-DEN-ATL vs MSP-MCO-ATL where the nonstop is about 2.5 hours. Fix: add to limitations and the Phase 1 backlog.
>
> Requirements coverage: all FR and SC items implemented and tested, except FR-027/SC-005 partial (finding 2) and FR-033/SC-001 failing off Windows (finding 1).

### Implementer responses (round 1)

All findings were fixed; none are deferred.

1. **CRLF reports (BLOCKING): fixed.** Every report and JSON file is now written with `newline="\n"` (`stages.write_json`, summary.json, summary.md, `cli._write_json`). `test_report_files_use_lf_line_endings` asserts there is no `\r` in any report file. `reports/phase0/` was regenerated, and none of its files contains `\r`.
2. **Partner minimum never varied (BLOCKING): fixed.** `sensitivity.scenario_rules` now moves every minimum (default, partner and per-hub) by the scenario's difference from the default, so partner connections use 35, 45 and 60 minutes. New tests: `test_scenario_shifts_every_minimum_connection_time`, and `test_partner_itinerary_threshold_changes_across_scenarios` (partner feasible days go 3, 3, 0 across mct20/30/45). Spec FR-027, methodology and sensitivity docstring updated. With real data: 225 pairs are now assumption-sensitive (was 221) and there are 221 showcase examples (was 222). The HNL-SEA partner pair is now compared in all 26 scenarios.
3. **Scenario coverage undisclosed: fixed.** `ComparablePair.scenarios_compared` was added (data model updated). summary.md gives it per showcase row and as a distribution, and ADR-0012 states it: 67 of 221 were compared in all 26 scenarios, 114 in 17, and 40 in 11. GO also holds on the 67 fully compared examples (7 hubs, 13 pairs).
4. **Layover below the feasibility threshold undisclosed: fixed.** The showcase table shows both scheduled layovers and flags "(tighter than threshold)". summary.md and ADR-0012 state that this applies to 54 of 221 examples, and the mechanism is explained in the methodology. Test: `test_showcase_section_discloses_scenarios_compared_and_tight_layovers`.
5. **`verify` scope and Python patch version: fixed.** `verify` now also compares summary.json, summary.md and quality.json byte for byte with the rerun. The manifest records Python as major.minor (`3.13`), and `pipeline/.python-version` pins 3.13.
6. **Precision: fixed.** Rates are shown in whole percent, and differences and confidence limits in whole points. Airport weather shares keep one decimal, since each is based on 50,000 or more departures. The rule is documented in methodology "Precision" and applied in report.py, the notebook and ADR-0012. Full-precision values remain in summary.json and Parquet.
7. **Partial flights sort order: fixed.** flights.parquet is now sorted by every FlightRecord column.
8. **Document claims: fixed.** ADR-0012 now uses the manifest's runtime (4.7 min, from `runtime_min: 4.67`) and says it was measured on a 16-core machine, not the 4-core reference. The methodology now says `acquire` stops on a checksum mismatch, while `run --no-acquire` and `verify` detect changed files through output hashes.
9. **Detours: fixed.** Added to the methodology limitations and to ADR-0012's consequences as a Phase 1 candidate.

Checks after the fixes: 253 tests pass, ruff and pyright are clean, and `flight-pipeline verify` on real data reports all 14 outputs and the committed report files identical.

Not addressed in code: test-first ordering can't be shown from commit history, because the work is uncommitted. Committing is the owner's call.

---

## Round 2 (2026-11-24): APPROVE

> **Verdict:** APPROVE. Both round-1 blockers are fixed and verified (0 CR bytes in all reports; partner MCT shifts per scenario, tested 3/3/0). Round-1 SHOULD-FIX fixes hold (`scenarios_compared` matches 67/114/40; tight-layover disclosure; whole-percent precision; byte-for-byte `verify`; total flights sort). Test-first ordering and committing spec files with code remain open until the owner commits.
>
> **Checks run:** pytest 253 passed; ruff check passed; ruff format 56 files formatted; pyright 0 errors; `uv lock --check` up to date; `flight-pipeline verify` (real data) exit 0, 14 outputs identical; 0 CR bytes in `reports/phase0/*`. ADR-0012 claims re-derived from the derived Parquet tables: 67 fully compared in 13 pairs, 221 examples, 7,801,389 rows.
>
> 1. **[SHOULD-FIX] Showcase pairs can compare itineraries that almost never flew on the same dates, while the CI is called "paired".** `compare.py:98-116` resamples the union of dates with no minimum overlap. `DEN-DFW-SEA:AA2612+AS543` (outcomes Oct–Jan) vs `AA2612+AS365` (Jun–Sep) share 0 dates but are a +15 point showcase (CI 3–27); 12 of 221 showcases share fewer than 30 dates, 20 share less than half the smaller sample; the summary headline LGA-LAX row shares 23. `test_no_overlap_or_empty_returns_none` only tests empty input. GO still holds with a 30-shared-day requirement (209 examples). Fix: require a minimum number of shared dates, report shared days per pair, test the disjoint case, update CI text, methodology and ADR-0012.
> 2. **[SHOULD-FIX] Constitution amendment labelled PATCH but changes a principle's done criterion, and is bundled uncommitted with the feature.** Principle III's exemption is a material change (MINOR per Governance), and Governance requires an amendment commit that explains the reason. Fix: bump to 1.1.0 and commit it separately before the feature.
> 3. **[SHOULD-FIX] Spec edge case "same flight number on several segments in one day" has no test (FR-034).** The code handles it (origin is in the identity), but no fixture would catch a regression. Fix: add a two-segment flight number to the fixture and assert both segments are ok and pair correctly.
> 4. **[SHOULD-FIX] A season with no weather-affected departures shows 0%, but the spec says "unknown".** `hubs.py` stores 0.0; only the all-zero airport gets an unknown peak. No effect on real data. Fix: return null for that season and test it, or change the spec wording.
> 5. **[NIT]** Multiple comparisons (1,144 pairs tested at 95%) not listed as a limitation; "statistically clear" overstates single examples.
> 6. **[NIT]** `contracts/outputs.md` flights sort order differs from the code (all FlightRecord fields).
> 7. **[NIT]** `data-model.md` says "about 7.5 million rows"; actual 7,801,389.
> 8. **[NIT]** ADR-0012 Context says order doesn't reverse "in any of the 27 scenarios", though most examples were checked in 11 or 17.
> 9. **[NIT]** `altair` dependency missing from plan.md.
>
> Requirements coverage: all pass, except FR-029 partial (finding 1) and FR-034 partial (finding 3).

### Implementer responses (round 2)

1. **Non-overlapping "paired" comparisons: fixed.** `ComparablePair.shared_days` was added: the number of dates on which both itineraries have a paired outcome. `is_showcase` now requires `shared_days >= min_sample_days` (30), and the showcase table shows "Shared dates". Spec FR-029, the data model, methodology and the CI method text were updated. Tests: `test_each_condition_is_required` (29 and 0 shared dates are rejected) and `test_shared_days_counts_dates_both_have_outcomes` (including disjoint dates). Real data: 209 showcase examples (was 221), all with at least 32 shared dates, still in 15 pairs across 7 hubs. GO holds, and 67 examples were compared in all 26 scenarios (13 pairs, 7 hubs). ADR-0012 and the roadmap were updated.
2. **Constitution version: fixed in part.** Bumped to 1.1.0 (MINOR), and plan.md now cites v1.1.0. A separate commit for the amendment is the owner's call, since nothing in this work has been committed. Recommended order: commit the constitution amendment first, with the reason "Principle III: phases without a deployable deliverable are done when their roadmap exit criterion is met", then the feature.
3. **Multi-segment flight number: fixed.** The fixture now has WN501 flying CMH→ORD and then ORD→DEN on 2026-01-10. `test_same_flight_number_on_two_segments_are_distinct_flights` asserts both segments are `ok`. `test_itinerary_using_both_segments_of_one_flight_number` asserts the itinerary is paired with 60 minutes of slack.
4. **Season with no weather-affected departures: fixed.** That season is now null (unknown) and can't be the peak, as the spec says. `test_metrics` asserts this, and the data model and methodology were updated. There is no change on real data.
5. **Multiple comparisons: fixed.** Added to the report's limitations, the methodology and ADR-0012's consequences.
6. **Flights sort order in contract: fixed.** `contracts/outputs.md` now lists every FlightRecord column in model order.
7. **Row count: fixed.** The data model now says 19 rows were dropped and 7,801,389 remain.
8. **ADR-0012 wording: fixed.** It now says "doesn't reverse in any sensitivity scenario where both itineraries qualify".
9. **altair missing from plan: fixed.** plan.md now lists tzdata, marimo and altair.

Checks after the fixes: 258 tests pass, ruff and pyright are clean, and `flight-pipeline verify` on real data reports all 14 outputs and the committed report files identical (runtime 4.7 min).

---

## Round 3 (2026-11-24): APPROVE

> **Verdict:** APPROVE. No blocking findings. All checks pass (258 tests, ruff, format, pyright, `uv lock --check`); `verify` on real data reproduces all 14 outputs and the committed report files byte for byte; ADR-0012 claims re-derived from the derived tables (209 showcases; scenarios compared 67/114/28; fewest shared dates 32; 49 tighter than threshold; 443 of 445 sufficient).
>
> 1. **[SHOULD-FIX] MCT scenarios change the paired-day sample, not only the threshold; undisclosed.** `feasibility.py:112` matches outbound flights only at or beyond the scenario minimum, so stricter scenarios drop the tightest days as "not connecting" instead of failing them; 29 of 417 itineraries get a higher rate at mct45 (e.g. `DTW-MCO-ATL:DL1455+DL1658`: 67.6% on 287 days at mct30, 74.5% on 145 days at mct45); 138 of 209 showcases include an itinerary whose sample changes. Re-scoring the default days at each threshold reverses 2 of 209 showcases; GO unaffected. Fix: decouple matching from the scenario minimum, or document the behavior (methodology, research R6, ADR-0012) and pin it with a test.
> 2. **[SHOULD-FIX] Seasonal weather shares missing from the committed hub report (FR-012, FR-007).** The peaks (e.g. LAS winter 1.18% vs summer 1.01%) can't be checked from `reports/phase0/`. Fix: add the four seasonal shares to the hub table, test, regenerate.
> 3. **[SHOULD-FIX] Nothing committed:** constitution amendment bundled with the feature; test-first unverifiable; T068 open. Fix: commit the amendment first with its reason, then the feature with specs, code, reports and review.md.
> 4. **[NIT]** HHMM validity accepts minutes ≥ 60 (e.g. `1275`), though docs say bad HHMM values are dropped; methodology says "negative" but code drops non-positive. 0 such rows in real data.
> 5. **[NIT]** `scenarios_compared` overcounts if a scenario has no result rows at all (it is absent from `rates`). No effect on real data.
> 6. **[NIT]** `od_pairs_without_itineraries` entries are `"ORIGIN-DEST (scenario_id)"`, but data-model says `ORIGIN-DEST` codes.
> 7. **[NIT]** Seasonal shares stored unrounded, against research R8 (no effect: deterministic integer division).
>
> Requirements coverage: all pass; FR-012 partial (finding 2), FR-027 pass with method caveat (finding 1).

### Implementer responses (round 3)

1. **MCT scenarios change the day sample: answered, kept and documented.** The behavior is intended: a scenario's minimum connection time is the minimum an airline would sell. Under a stricter minimum, a day whose scheduled layover is below it isn't a sellable connection, so it's excluded as "not connecting" rather than counted as a failure. This is now stated in methodology "Sensitivity" (including the 29 of 417 itineraries whose rate rises at 45 minutes and the median moving from 92% to 91%), research R6 and ADR-0012 (re-scoring on the default days would reverse 2 of 209 examples, with no effect on the decision). The test `test_day_below_scenario_minimum_is_not_connecting_rather_than_failed` pins it. Decoupling the matching window would answer a different question ("same days, stricter threshold") and is noted as an option for Phase 3 calibration work.
2. **Seasonal weather shares: fixed.** The hub table now has a "Weather by season (W / Sp / Su / Au)" column with one decimal ("n/a" when unknown), covered by `test_hub_section_shows_seasonal_weather_shares`. The reports were regenerated; for example, LAS shows 1.2% / 0.6% / 1.0% / 0.7% with a winter peak.
3. **Commits: open, for the owner.** No commits were made, because committing needs the owner's go-ahead. Recommended sequence: (1) commit `.specify/memory/constitution.md` alone, with the reason "Principle III: phases without a deployable deliverable are done when their roadmap exit criterion is met (v1.1.0)"; (2) commit the feature: specs (including this review.md), code, config, reports and docs.
4. **HHMM minutes of 60 or more: fixed.** Scheduled times with minutes ≥ 60 are now invalid schedules, dropped and counted (`test_hhmm_with_minutes_of_60_or_more_is_an_invalid_schedule`). The methodology now says "non-positive" elapsed time.
5. **`scenarios_compared` with a scenario that has no results: fixed.** `reversal_flags` takes the full list of scenario ids, and a scenario with no rows counts as not compared (`test_scenario_without_any_results_counts_as_not_compared`).
6. **`od_pairs_without_itineraries` format: fixed.** The data model now documents `"ORIGIN-DEST (scenario_id)"`.
7. **Unrounded seasonal shares: fixed.** They are now rounded to 6 decimals.

Checks after the fixes: 262 tests pass, ruff and pyright are clean, and `flight-pipeline verify` on real data reports all outputs and the committed report files identical. The results are unchanged: 209 showcase examples, GO.

---

## Round 4 (2026-11-24): APPROVE

> **Verdict:** APPROVE. No blocking findings. Checks: 262 tests passed; ruff, format and pyright clean; `uv lock --check` up to date; `verify` on real data exit 0 with 14 outputs and the report files identical; ADR-0012 counts re-derived.
>
> 1. **[SHOULD-FIX] Most showcase examples are large detours on routes with frequent nonstops, but ADR-0012 calls this "some itineraries" and claims breadth.** In 180 of 209 examples even the faster itinerary takes more than 1.5× the nonstop time, and in 88 both exceed 2×. Only 27 examples (LGA-LAX 25, BOS-SFO 2) are within 1.5× or have no nonstop. ADR-0012's highlighted DTW-MCO-ATL takes 363/306 min against a 122-min nonstop. GO still holds on the plausible subset (≥ 3 examples; hubs ATL, DEN, DFW, LAX, ORD), but the stated breadth does not. Fix: quantify the detour share, state GO on the subset, choose plausible highlighted examples, and make a detour limit a required Phase 1 rule.
> 2. **[SHOULD-FIX] Recurrence scenarios can't reverse any pair, so "compared in N of 26 scenarios" overstates robustness.** Rates are identical across recurrence 50/60/75% in all 5,271 itinerary × (MCT, cutoff) combinations. "All 26" and part of "17" cover the same 8 distinct settings; the other 29 "17" and all 28 "11" examples cover only 5 and never MCT 45. Fix: report distinct (MCT, cutoff) settings compared, state that recurrence tests qualification not order, and correct ADR-0012 and the roadmap.
> 3. **[SHOULD-FIX] Nothing committed (carried over).** The constitution amendment must be committed alone with its reason, then the feature; T068 is open.
> 4. **[NIT]** The hour of `CRSArrTime` isn't range-checked (`2530` is read as 01:30). No effect observed.
> 5. **[NIT]** Pattern layovers use local clock times while the plan claims full UTC compliance. No result changes; record a justified exception or use UTC medians.
> 6. **[NIT]** README says 4 GB and quickstart 5 GB; the quickstart check list omits `ruff format --check`, which CI runs.

### Implementer responses (round 4)

1. **Detours: fixed in the decision record.** I re-derived the figure: 27 of 209 examples have both itineraries within 1.5× the nonstop time (or no nonstop). They fall in 2 pairs, LGA-LAX and BOS-SFO, across 5 hubs. ADR-0012 was rewritten around this. The title now reads "GO, on a narrower base than the raw count suggests"; the decision table has an "All examples" column and a "Plausible routings only" column; the highlighted examples now come from LGA-LAX and BOS-SFO; and a detour limit is listed as a **required** Phase 1 rule. The methodology and roadmap were corrected to match. The pipeline itself is unchanged, because a detour limit is a new itinerary rule that belongs in the Phase 1 spec, not in this one.
2. **Recurrence scenarios: fixed in the docs.** I confirmed that recurrence never changes a rate (0 of 5,271 combinations differ). Counting distinct (MCT, cutoff) settings including the default: 152 examples were checked at all 9 settings and 57 at 6, and those 57 were never checked at 45 minutes. The methodology now says recurrence tests only which itineraries qualify. ADR-0012 and the roadmap now use the settings count instead of "26 scenarios", and Phase 1 is told to report settings rather than scenario counts. The `scenarios_compared` field is unchanged and keeps its exact definition.
3. **Commits: still open, for the owner.** Same recommendation as in round 3.
4. **CRSArrTime hour: deferred.** It has no observed effect: scheduled arrivals that disagree with departure plus elapsed time are already counted (`sched_arr_mismatch`, 35 rows). It will be fixed with the Phase 1 normalizer changes.
5. **Local-time layovers: recorded.** This is now a justified deviation in plan.md Complexity Tracking.
6. **Docs: fixed.** The README says 5 GB, and the quickstart lists `ruff format --check`.

---

## Round 5 (2026-11-24): APPROVE

> **Verdict:** APPROVE. No blocking findings. Checks: 262 tests passed; ruff, format and pyright clean; lockfile up to date; `verify` on real data identical. Default-scenario counts for four itineraries were recomputed independently from `flights.parquet` and match exactly; every ADR-0012 and methodology figure was re-derived and holds.
>
> 1. **[SHOULD-FIX] Itineraries qualify on two separately computed medians, so many "recurring" itineraries rarely connect.** 95 of 445 analyzed itineraries connected on fewer than 60% of their inbound days (15 on fewer than 30%); 85 of 209 showcases include one. `BOS-LAX-SFO:DL479+DL2272` has a median layover of 37 minutes, but its daily layovers are mostly negative and it connected on 54 of 363 days. Of the 27 plausible-routing examples, 15 include such an itinerary (both BOS-SFO and 13 of 25 LGA-LAX). Without them, 12 examples remain, all LGA-LAX, across ATL, ORD and DEN; GO still holds on one market. Fix: disclose the connecting-day share, caveat or replace BOS-SFO, restate the subset, and add a connection-level recurrence rule to Phase 1.
> 2. **[SHOULD-FIX] The plausible-subset and settings figures ADR-0012 rests on come from untested ad-hoc queries outside `verify`.** Fix: move them into tested pipeline code written to summary.json, or commit the exact query beside the ADR and say they are outside the reproducible pipeline.
> 3. **[SHOULD-FIX] Nothing committed (carried over).**
> 4. **[NIT]** On Linux and macOS, `zoneinfo` reads the system tz database before the pinned `tzdata` package, so the pin only controls Windows. No effect for US zones in 2025-2026. Fix: `zoneinfo.reset_tzpath([])` or `PYTHONTZPATH=""`, or correct the wording.

### Implementer responses (round 5): held for the owner

The review loop reached APPROVE in rounds 2 to 5. Every BLOCKING finding is fixed, and every earlier SHOULD-FIX is fixed or answered. Round 5's findings 1 and 2 are not fixed here. They show that the evidence behind GO has narrowed from 209 examples to 12, in one market, so continuing to patch the decision record would be the implementer deciding the go/no-go question. The constitution leaves the merge decision to the owner. The open options are:

- **(a) Accept GO on the narrow evidence.** Update ADR-0012 to "12 examples in LGA-LAX", add the round-5 disclosures, and carry the detour limit and connection-level recurrence into Phase 1 as required rules.
- **(b) Fix the itinerary rules in Phase 0 and rerun.** Amend the spec with a detour limit (for example 1.5× nonstop) and a recurrence rule measured on actually connecting days, implement both test-first, rerun, and decide GO/NO-GO on the corrected results. Findings 1, 2 and 4 would all be fixed in code.

Finding 3 (commits) also needs the owner. Task T068 stays open until the owner decides.

---

## Round 6 (2026-11-24): CHANGES REQUIRED

Owner decision after round 5: option (b), amendment 1 (DB1B sold routings, connection-level recurrence, one period July 2024 to June 2025). Round 6 reviews the amended feature.

> **Verdict:** CHANGES REQUIRED. One blocking finding. Checks: 296 tests passed; ruff, format and pyright clean (run from `pipeline/.venv`, `uv` not on PATH); `verify` on real data identical (16 outputs). Every ADR-0012, summary.md and roadmap figure was re-derived from the derived tables and matches. For all 229 default itineraries `(paired_days + excluded_quality) / 365` equals `connect_share` exactly, so connection-level recurrence agrees with the feasibility stage's daily matching. SC-009 holds for all 47,571 itineraries.
>
> 1. **[BLOCKING] Unmapped DB1B selling-airline codes are dropped without being reported** (spec edge case, FR-034). `prepare/db1b.py` counts only `--` legs. Codes that are neither on-time marketing airlines nor mapped (SY 14,212, LF 12,037, KG 7,494, MX 5,082, 9K 4,919, 9X 3,330, 3M 3,217 and smaller; about 51,000 sampled passenger-legs) appear nowhere in the outputs. No test covers the case. Fix: compute and report them per code with a share, in `sold_routings.json`/Finding/summary.md; test with the `legacy_code` row unmapped.
> 2. **[SHOULD-FIX] The report states a count of settings compared, not which settings** (FR-027). All 22 showcases at "6 of 9" were never compared at MCT 45, including four headline rows; 19 of them are the tight-layover examples. ADR-0012's "never reversing" suggests they survived the strictest setting. Fix: list the missing settings per showcase and say so in ADR-0012.
> 3. **[SHOULD-FIX] Some ADR-0012 figures come from ad-hoc queries** (SC-010): the non-tight subset's pairs and hubs, the 17 cross-hub examples, and "59 of 76 slower than 1.5 times the nonstop, about 2.8 times". Fix: compute them in `stage_report` with a test, or label them as outside the pipeline.
> 4. **[SHOULD-FIX] Nothing is committed; the constitution amendment is bundled with the feature; T083 is ticked although it includes T068** (carried over). Fix: owner's call; commit the constitution amendment alone, then the feature; untick T083.
> 5. **[NIT]** data-model.md still cites the old period's row counts (19 invalid, 7,801,389 flights).
> 6. **[NIT]** The ADR-0012 MCO-LGA example row gives no rates or sample sizes.
> 7. **[NIT]** spec.md header still says Draft.

### Implementer responses (round 6)

1. **Unmapped selling airlines: fixed.** `prepare.db1b.unmapped_airlines` compares the sold routings' codes (after `carrier_map`) with the on-time marketing airlines. `stage_report` records each code's sampled passengers (routings counted once per code) and the share of 2-coupon passengers on such routings (each routing once) in the new Finding fields `db1b_unmapped_airlines` and `db1b_unmapped_airline_share`. summary.md states both. On real data the share is 0.3% (LF, KG, SY, 9K, 9X, 3M, MX and smaller codes, mostly regional and foreign airlines). Test: `test_db1b.py::test_unmapped_selling_airlines_reported` (the `legacy_code` row is reported as `US` 4 without a map, and nothing is reported with `US = "AA"`); `test_report.py::test_summary_reports_unmapped_selling_airlines`.
2. **Settings not compared: fixed.** `sensitivity.missing_settings` returns the settings each pair was not compared at, and `report.describe_missing_settings` puts them into words. The showcase table now reads, for example, "6 of 9 (not at minimum connection 45 min)", and the disclosure sentence counts the examples per note ("22 not at minimum connection 45 min"). ADR-0012 says the 22 were never checked at 45 minutes, and that 19 of them are the tight-layover examples. Tests: `test_missing_settings_described_per_showcase`, `test_showcase_section_names_missing_settings`.
3. **Ad-hoc figures: fixed.** `report.showcase_breakdown` computes every subset ADR-0012 cites: examples per pair, cross-hub examples, examples, pairs and hubs without tight layovers, examples slower than 1.5 times the median nonstop time (median scheduled elapsed time per airport pair, any airline) and the largest ratio, and examples without a nonstop. It is written to summary.json (`showcase_breakdown`) and to a new summary.md section, so `verify` covers it. The ADR now cites that section. Tests: `test_showcase_breakdown_counts_subsets`, `test_breakdown_section_states_each_subset`. The real-data values match the review's re-derivation, except "about 2.8 times", which is now the pipeline's maximum, 2.9.
4. **Commits: open, for the owner.** T083 is unticked until T068 closes. The recommended order is unchanged: commit the constitution amendment alone, with its reason, then the feature.
5. **Data model figures: fixed** (2 invalid rows, 7,671,287 flights).
6. **MCO-LGA row: fixed** (93% of 336 days against 66% of 265 days).
7. **Spec status: fixed** ("Approved (amended by amendment 1, 2026-11-24)").

After the fixes: 302 tests passed; ruff, format and pyright clean; the report was regenerated, and `verify` on real data reports "identical: 16 outputs match the committed manifest".

---

## Round 7 (2026-11-24): APPROVE

> **Verdict:** APPROVE. No blocking findings. Checks: 302 tests passed; ruff, format and pyright clean; `verify` on real data identical (16 outputs, 7 min 12 s); report hashes match the manifest; no CR bytes. ADR-0012 headline figures and SC-009 re-derived from the derived tables and match. A weekly-block bootstrap also keeps all 76 intervals above zero.
>
> 1. **[SHOULD-FIX] The "scheduled layover" is a difference of two separate medians.** When a flight changes schedule during the year it misstates the layover on the days the itinerary connects. Of 229 analyzed itineraries, 96 differ from the median of daily scheduled layovers on connecting days by 5 minutes or more (largest 35; ATL-LAX-SEA DL301+DL1551 reported 57, daily 92). Only 11 of the 19 "tighter than threshold" showcases are tight by daily median (MCO-ATL-LAX DL1463+DL501 43 vs 54; LGA-ATL-MCO DL988+DL1497 42 vs 47; COS-DEN-DRO UA5634+UA1217 43 vs 51), so "19" and "57 remain" become 11 and 65. Step 2 also excludes 2 sold itineraries that connect on at least 60% of days (BOS-LAX-SFO DL479+DL2272, 20 min by medians; BNA-ATL-DEN DL3001+DL530, 248). Median travel time has the same issue for comparability (3 showcases change). GO is unaffected. No test covers the tight rule or a schedule change. Fix: compute layover and travel from daily schedules on connecting days; use them for the tight flag, comparability and the report; make step 2 a pre-filter or document it; add a schedule-change fixture and a tight-rule test.
> 2. **[SHOULD-FIX] The committed manifest has no runtime** (`runtime_min: null`), because a standalone `report` overwrote the manifest written by `run`. SC-008, T062 and ADR-0012's "7.1 minutes" have no committed evidence. Fix: rerun `run --no-acquire`; make `report` keep the recorded runtime or say it was not measured.
> 3. **[SHOULD-FIX] Nothing committed; the constitution amendment is bundled; T068 and T083 open** (carried over). tasks.md says T062, T063 and T066 "are reopened above" while they are ticked.
> 4. **[NIT]** ADR-0012 gives the wrong reason for 3 of the 22 examples not compared at MCT 45: SAN-LAX-IAD UA4723+UA1140 (59 min) drops out because it connects on too few days, not because of its layover.
> 5. **[NIT]** The tzdata pin controls the rules only on Windows (round-5 NIT 4, not answered): on Linux and macOS `zoneinfo` reads the system database first.

### Implementer responses (round 7)

1. **Layover from two medians: fixed for every reported value; the rule-2 pre-filter is answered.**
   - `median_layover_min` and `median_travel_min` are now medians of the daily scheduled values (UTC) on the days the two flights connect, computed in step 4 from the same ASOF match that counts connecting days. The tight flag, comparability, the report columns and the breakdown all use them. The tight rule is now `compare.tight_itineraries`, used by `stage_report` and tested directly.
   - New fixture: UA7002 and UA7003 change schedule at different times. The pattern medians give a 100-minute layover; the daily median is 40 (tight). Tests: `test_layover_and_travel_come_from_daily_schedules_on_connecting_days` and `test_tight_itineraries_use_their_own_threshold`. Exclusion counts were re-derived by hand.
   - Real-data rerun: 81 showcase examples in 9 pairs across 5 hubs, still GO. 11 are tight; the other 70 cover all 9 pairs and 5 hubs. 58 were compared at all 9 settings and 23 at 6. Pair selection changed slightly, because comparability uses the corrected travel times: COS-DRO dropped out and LAX-IAD came in. ADR-0012, the roadmap and the methodology now use these figures.
   - **Rule 2 stays a pattern-level pre-filter.** It keeps the daily matching affordable across the 30-airport candidate pool (all sold candidates times 365 days otherwise). That it can exclude an itinerary that would connect when the two flights change schedule at different times (2 in the selected pairs, per this review) is now stated in the methodology, in the `build_itineraries` docstring and in data-model.md. ADR-0012 makes "apply the layover limits only through the daily matching" a Phase 1 requirement. GO does not depend on it.
2. **Runtime evidence: fixed.** `write_manifest` now keeps the runtime of the last full run when a stage runs on its own, and records when it was measured (`runtime_measured_at`); with no earlier measurement it says so (null). Tests: `test_manifest.py`. The committed manifest comes from a full `run --no-acquire`: `runtime_min` 7.87, `runtime_exceeded` false.
3. **Commits: open, for the owner** (unchanged). The tasks.md purpose line no longer says T062, T063 and T066 "are reopened above"; it says they are rerun for the amended feature under T083, which stays open until T068 closes.
4. **MCT 45 reasons: fixed.** ADR-0012 now gives both reasons: for the 11 tight examples the lower layover is below 45 minutes; for the other 12, at 45 minutes one itinerary no longer connects on enough days.
5. **tzdata pin: fixed.** Importing `flight_pipeline` calls `zoneinfo.reset_tzpath(to=[])`, so the rules always come from the pinned `tzdata` package on every operating system. Test: `test_timezones.py::test_time_zone_rules_come_from_the_pinned_tzdata_package`. research.md R3 and the methodology say so.

After the fixes: 308 tests passed; ruff, format and pyright clean; full real-data `run --no-acquire` (7.9 minutes), and `verify` reports "identical: 16 outputs match the committed manifest".

---

## Round 8 (2026-11-24): APPROVE

> **Verdict:** APPROVE. No blocking findings. Checks: 308 tests passed; ruff, format and pyright clean; `verify` on real data identical (16 outputs; 7,671,287 flights, 7 hubs, 15 pairs, 235 itineraries, 541 comparable pairs, 120 sensitive, 81 showcases). The manifest records `runtime_min` 7.87 and `runtime_exceeded` false; every source is pinned; no secrets; attribution present.
>
> 1. **[SHOULD-FIX] Southwest contributes 0 itineraries, and the report and ADR-0012 imply every major network is represented.** Itineraries are identified by flight number and each pattern must recur on at least 60% of days. WN reassigns flight numbers often: the median WN pattern runs on 10 days a year, and only 15 of 82,097 WN patterns recur on 60% of days (DL 3,166 of 21,853). `itineraries.parquet` has 0 WN itineraries of 47,571 (DL 35,058, UA 10,291, AA 2,197, F9 15, AS 10), although WN has 5,076 sold same-airline routings through the selected hubs (714,515 sampled passengers) and is about 18% of departures. AA is also underrepresented. FR-010 airline coverage is met only formally. GO is unaffected. Fix: report itineraries and sold routings per airline from `stage_report` with a test; add a limitation; correct ADR-0012; record a Phase 1 requirement to identify itineraries by schedule rather than flight number, or justify excluding WN.
> 2. **[SHOULD-FIX] Nothing committed; the constitution amendment is bundled** (carried over). T068 and T083 unticked.
> 3. **[NIT]** The hub section hard-codes "equally weighted"; render it from `[hubs].weights`.
> 4. **[NIT]** The go criterion counts both itineraries' hubs, so a single cross-hub comparison gives "2 hubs"; state this in the methodology.

### Implementer responses (round 8)

1. **Airline coverage: disclosed, by the pipeline; the rule change goes to Phase 1.**
   - `report.airline_coverage` computes, per marketing airline, the itineraries through the selected hubs and the sampled DB1B passengers on sold same-airline routings through them. `stage_report` writes them to a new Finding field, `airline_coverage`, and to a new summary.md section, "Airlines covered", which names the airlines with no itinerary. Because the figures are in the reports, `verify` covers them.
   - On real data: AA 2,197 itineraries (2,351,532 sold passengers); DL 35,058 (2,048,616); UA 10,291 (1,726,378); WN 0 (750,552); F9 15; AS 10. The airlines with no itinerary are WN, NK, HA, B6 and a few foreign codes with 1 or 2 passengers.
   - A new limitation in the report and the methodology says itineraries are identified by flight number.
   - ADR-0012 now says the network coverage is formal. Its hub rationale names the WN and AA gap, and it lists a Phase 1 requirement: identify itineraries by airline, route and departure-time window, or justify and disclose the exclusion.
   - Changing the identity rule in Phase 0 would mean another spec amendment. GO does not depend on it.
   - Tests: `test_airline_coverage_counts_itineraries_and_sold_passengers`, `test_airline_section_names_airlines_without_itineraries`, `test_limitations_name_flight_number_identity`.
2. **Commits: open, for the owner** (unchanged).
3. **Hub weights text: fixed.** `hub_section` takes the configured weights and says "equally weighted" only when they are equal. Test: `test_hub_section_states_configured_weights`.
4. **Hubs of an example: fixed in the methodology.** An example counts toward the hubs of both its itineraries.

After the fixes: 312 tests passed; ruff, format and pyright clean; the report was regenerated, and the manifest kept the measured runtime (7.87 minutes, measured 2026-11-25T06:10:14Z). `verify` reports "identical: 16 outputs match the committed manifest".

---

## Round 9 (2026-11-24): APPROVE

> **Verdict:** APPROVE. No blocking findings. Checks: 312 tests passed; ruff, format and pyright clean; `verify` on real data identical (16 outputs). Every rule's code read with no logic errors found; `showcase_breakdown` and `quality.json` figures match ADR-0012 and the methodology; attribution present; no secrets in untracked files.
>
> 1. **[SHOULD-FIX] The largest showcase market rests on a thin DB1B routing, and the report shows routing totals as if per itinerary.** `sold_passengers` is the routing total, shared by every flight pair on it. MCO-ATL-LGA on DL has 44 sampled passengers for the year (about 440 real), shared by 36 itineraries, and supplies 37 of 81 examples; LGA-ATL-MCO has 64 over 33 itineraries. The headline row's "44 / 44" reads as per itinerary. GO unaffected. Fix: rename the column, report the itineraries sharing each routing from the pipeline, and state the MCO-LGA figure in ADR-0012.
> 2. **[SHOULD-FIX] FR-021 "cancellation takes precedence over diversion" has no test.** Swapping the two `CASE` branches in `classify` passes all 312 tests. Fix: a case with a diverted inbound and a cancelled outbound, asserting `cancelled`.
> 3. **[NIT] `merge_run` carries a measured runtime across configuration or data changes.** Fix: carry it over only when `config_sha256` and `sources` match.
> 4. **[SHOULD-FIX, carried over]** Nothing committed; constitution amendment bundled; T068 and T083 open.

### Implementer responses (round 9)

1. **Routing totals: fixed.** The showcase column is now "Sold passengers on routing A / B (DB1B sample; shared by its itineraries)". It shows, for example, "44 on 36 itineraries": `report.routing_itineraries` counts the qualifying itineraries sharing each routing, so the figure comes from the pipeline and `verify` covers it. ADR-0012 states the MCO-LGA figure (44 sampled passengers shared by 36 itineraries; LGA-MCO 64 over 33). ADR-0012 and ADR-0013 now say the itineraries are *on* sold routings. Tests: `test_showcase_section_discloses_settings_compared_and_tight_layovers` (updated) and `test_routing_itineraries_counts_flight_pairs_per_routing`.
2. **FR-021 precedence: fixed.** `test_daily_outcomes.py::test_cancellation_takes_precedence_over_diversion` classifies days with both flags, only diverted, and only cancelled. Swapping the `CASE` branches now fails it. The code was already correct, so the test passed when added.
3. **Runtime carry-over: fixed.** `merge_run` keeps an earlier runtime only when `config_sha256` and `sources` match the previous manifest, and otherwise records it as not measured. Test: `test_runtime_not_carried_over_when_config_or_sources_changed`.
4. **Commits: decided by the owner.** The owner accepted GO and approved two commits once the review approves: the constitution amendment alone, then the feature.

After the fixes: 315 tests passed; ruff, format and pyright clean; the report was regenerated (the runtime of 7.87 minutes was kept, because config and sources are unchanged), and `verify` reports "identical: 16 outputs match the committed manifest".

---

## Round 10 (2026-11-24): CHANGES REQUIRED

> **Verdict:** CHANGES REQUIRED. One blocking finding. Checks: 315 tests passed; ruff, format, pyright clean; `uv lock --check` up to date; `verify` on real data identical (16 outputs). Five headline itineraries recomputed independently from `flights.parquet` match exactly. A mutation run (25 one-line mutants of calculation code) killed 15; 7 survivors are real test gaps.
>
> 1. **[BLOCKING] summary.md silently drops the per-itinerary results appendix**, including the written definition of connection feasibility (`render_summary` takes `appendix` but never adds it). The contract (outputs.md) requires all default results in an appendix; the `test_results_*` tests only test `results_section` alone. Fix: add the appendix, test it, regenerate; also show `slack_min` and avoid "(min)" reading as "minimum".
> 2. **[SHOULD-FIX] The go criterion's both-hubs rule is untested** (mutant counting only the first hub survives). Fix: `go_criteria([("ORD","DFW"),("ORD","ORD"),("ORD","ORD")], 3, 2) == (True, True)`.
> 3. **[SHOULD-FIX] Some JSON outputs have no Pydantic model** (quality.json, sensitivity_summary.json, hub_selection.json, od_selection.json, sensitivity.json), contrary to Principle IV and the plan's claim. Fix: models validated on write and read, or a recorded exception.
> 4. **[SHOULD-FIX, carried over]** Nothing committed; constitution amendment bundled.
> 5. **[NIT]** Go/no-go status inconsistent: ADR-0012, the ADR index and the roadmap say Proposed while review.md records the owner's acceptance.
> 6. **[NIT]** Untested boundaries: the outbound latest-departure boundary in `feasibility.py` (240-minute itinerary's daily outcomes), the tie case in the reversal test (never decisive), and the rate at exactly the minimum sample.

### Implementer responses (round 10)

1. **Results appendix: fixed.**
   - `render_summary` now includes the appendix, after the data-quality section and before attribution. summary.md therefore contains the "Connection feasibility" section again: its definition, and every selected pair's results with failure counts, slack and excluded days.
   - The slack column is now "Slack min / p10 / p50 / p90 (minutes)" and includes the minimum (FR-023).
   - Test: `test_report.py::test_summary_includes_results_appendix_with_definition`, which renders a summary with an appendix and checks its heading, definition and position.
2. **Both-hubs rule of the go criterion: tested.** `test_showcase.py::test_go_criteria` now asserts `go_criteria([("ORD","DFW"),("ORD","ORD"),("ORD","ORD")], 3, 2) == (True, True)`, and the mirrored case. The code was already correct.
3. **JSON outputs: models added.**
   - New Pydantic models in `models.py`: `QualitySummary` (quality.json), `SoldRoutingsSummary`, `HubSelectionMeta`, `OdSelectionMeta`, `SensitivityMeta`, `ScenarioSummary` (sensitivity_summary.json, through a `TypeAdapter`), `SourceRecord` (sources.json) and `Manifest`.
   - `write_json` and `read_json` in `stages.py` validate against the model whenever one is given, and every writer and reader passes one. `cli.prepare` validates quality.json and sold_routings.json before writing them.
   - The bytes written are unchanged.
   - Test: `test_json_outputs_have_models`; every stage exercises the validation end to end.
4. **Commits: decided by the owner.** The two commits follow once a review approves.
5. **Status consistency: fixed.** The owner accepted GO. ADR-0012 is now Accepted, its README row says Accepted, the roadmap marks Phase 0 complete, and the repository README states the result.
6. **Boundaries: tested.**
   - `test_daily_outcomes.py::test_outbound_at_the_maximum_layover_connects`: CMH-ORD-SAN AA3100+AA1506, at exactly 240 minutes, has 8 paired days and 2 quality exclusions, with no day not connecting.
   - `test_sensitivity.py`: a tie-only pair (e, f) is now decisive for "a tie is not a reversal".
   - `test_itinerary_results.py`: the rate is asserted at exactly the minimum sample.
   - Each test passed when added, so these were coverage gaps, not bugs.

After the fixes: 319 tests passed; ruff, format and pyright clean; the report was regenerated, and `verify` reports "identical: 16 outputs match the committed manifest".

---

## Round 11 (2026-11-25): APPROVE

> **Verdict:** APPROVE. No blocking findings.
>
> **Checks:**
> - 319 tests passed; ruff, format and pyright clean; `uv lock --check` up to date.
> - `verify` on real data identical (16 outputs).
> - A rerun with DuckDB limited to 4 threads took 17.8 minutes with identical outputs, which supports SC-008.
>
> **Independent recomputation:**
> - Daily outcomes of three showcase itineraries match the pipeline exactly.
> - One bootstrap interval: +6.9 to +19.3 against the pipeline's +6.9 to +19.5.
> - SC-009 holds for all 47,571 itineraries.
> - `connect_share` equals `(paired_days + excluded_quality)/365` for all 235 analyzed itineraries.
> - Hub metrics, manifest pins and wording checked.
>
> **Findings:**
> 1. **[SHOULD-FIX] No test covers `verify`'s byte comparison of the committed report files**, or its config/sources/packages comparison. A mutant that disables the byte check passes `test_determinism.py` and `test_cli.py`.
> 2. **[SHOULD-FIX, carried over]** Nothing committed; constitution amendment bundled; T068 open.
> 3. **[NIT]** ADR-0012 and the methodology misstate sample sizes. Analyzed itineraries have 219–365 paired days (at least 183 in any scenario), none near the 30-day minimum.
> 4. **[NIT]** The last day of the period can't connect to a next-day outbound, because July 2025 isn't loaded. This affects 539 of 47,571 eligibility itineraries by 1/365, and none of the 235 analyzed.
> 5. **[NIT]** The notebook shows routing totals as if per itinerary.
> 6. **[NIT]** `verify` extracts DB1B into `data/raw/db1b/extract/`, outside its temporary directory, contrary to contracts/cli.md.
> 7. **[NIT]** The forbidden-wording test checks only the results section, not the whole summary.
> 8. **[NIT]** The committed runtime was measured before the round 9–10 code changes; the manifest has no code identity.

### Implementer responses (round 11)

Round 11 approves. To close the review loop without another round of code changes, every remaining finding is answered here. Only factual corrections to the documents were made.

1. **`verify` byte-check test: deferred, recorded as a follow-up.**
   - The check works: every `verify` run in rounds 1–11 compared the committed files byte for byte and passed.
   - What is missing is a regression test. It is listed under "Phase 0 follow-ups" in the roadmap backlog, to be added at the start of Phase 1 before any change to `cmd_verify`.
2. **Commits: done as the owner decided.** The constitution amendment was committed alone with its reason, then the feature with its specs and this review. T068 and T083 are ticked.
3. **Sample sizes: fixed.** ADR-0012 now says "219 to 365 paired days at the default assumptions (at least 183 in any scenario)", and the methodology's precision sentence matches.
4. **End of period: answered.** None of the 235 analyzed itineraries is affected. It can move an eligibility itinerary that sits exactly at the threshold by 1/365, and no selected hub is near its eligibility minimum (PHX, the closest, has 36 against 15). Listed as a follow-up.
5. **Notebook column: follow-up.** The notebook is exploratory. summary.md, which ADR-0012 cites, shows the sharing ("44 on 36 itineraries").
6. **`verify` extraction directory: follow-up.** The contract will be met by passing a work directory under the temporary directory.
7. **Wording test scope: follow-up.** The whole summary was checked by hand in rounds 10 and 11 and has no passenger-outcome wording.
8. **Runtime provenance: answered.** The round 9–10 changes touched only reporting, tests and JSON validation, not the stages that dominate runtime. This review's independent 4-thread rerun (17.8 minutes) confirms SC-008. Adding code identity to the manifest is a follow-up.

**Review loop closed.** The final verdict is APPROVE (round 11). All BLOCKING findings from every round are fixed. Every SHOULD-FIX is fixed or answered above. The owner accepted GO (ADR-0012) and makes the merge decision.
