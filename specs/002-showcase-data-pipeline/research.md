# Research: Showcase Data Pipeline

Decisions for the open technical questions in [plan.md](plan.md). Each has the decision, the rationale and the alternatives considered. Phase 0's decisions ([specs/001 research](../001-bts-connection-experiment/research.md)) still hold unless replaced here.

## R1. Schedule-based itinerary identity

- **Decision:** a **schedule slot** replaces the flight pattern. A slot is a marketing airline, origin, destination and a cluster of scheduled local departure times. Each flight-day is assigned to a slot:
  1. For each (airline, origin, destination), collect every scheduled flight-day's local departure minute (DST-stable local time, as in Phase 0's pattern medians).
  2. Cluster the minutes in one dimension: sort them and start a new cluster wherever the gap to the previous minute is more than the window (default 30 minutes). A cluster wider than twice the window is split at its largest internal gap.
  3. A cluster with days that have several flights is split into k sub-slots, k being its largest number of flights on one day. On the days with k flights, flights are ranked by time (ties by flight number) and the ranks define the sub-slots and their reference times. On days with fewer flights, each flight goes to a free sub-slot that already carries its flight number, otherwise to the free sub-slot with the nearest reference time, otherwise to the lowest rank. Two regular schedules less than the window apart therefore stay two slots. Duplicate records of one flight-day (Phase 0 quality flags) count once.
  4. **Schedule changes are joined, not split.** A schedule that moves by more than the window during the period would otherwise become two partial slots, each possibly below the recurrence threshold. Sub-slots of the same airline and route are therefore joined into one slot when they don't overlap in time (the later starts at most 7 days after the earlier ends) and they share a flight number across the boundary. The join date is recorded as a schedule change (research R13). Each sub-slot is first cut into runs at gaps longer than 7 days, and runs are joined, so a change and a change back (a winter schedule: A, B, A) is one slot with two changes; runs of one sub-slot always stay in one slot, and a join is made only when the two slots never fly on the same day. Joins are made greedily in date order and are deterministic. Flight-number continuity is used only for this join; renumbering alone is handled by steps 1–3.
  5. The slot's reference time is the median departure minute over all its days; its flight numbers are recorded with the share of days each was used.
- **Itinerary identity** = inbound slot + outbound slot through a hub (same airline or a listed partner pair). The ID is deterministic: `{origin}-{hub}-{dest}:{airline}{HHMM}+{airline}{HHMM}`, using the slots' reference local departure times, with a suffix on the rare collision.
- **Rationale:** Southwest reassigns flight numbers but flies the same schedule; American also varies numbers by day. Clustering by time is what a traveler means by "the 2 pm Southwest flight to Denver". One-dimensional gap clustering is deterministic, explainable and fast.
- **Alternatives:** fixed clock bins (split identical schedules at bin edges); flight-number identity with alias merging (needs a table of aliases nobody publishes); route plus airline only (loses the time of day, which matters for reliability).

## R2. Layover limits only through daily matching

- **Decision:** drop the median-layover rule. Each candidate itinerary is matched daily (Phase 0's ASOF join: earliest outbound at or after inbound arrival plus minimum connection, within the maximum layover), and only connecting days count. To keep this affordable across the 30-airport hub pool, a **lossless bound pre-filter** runs first: from each slot's earliest and latest scheduled local times over the year, a candidate is dropped only when *no* combination of its times can produce a layover within the limits. This can never exclude an itinerary that would connect.
- **Order of rules** (replacing Phase 0's R12): airline-compatible slot pairs whose slots each recur (necessary condition) → bound pre-filter (lossless) → sold routing (DB1B) → daily matching with connection-level recurrence.
- **Days at the end of the period:** an inbound day whose matching window extends past the last loaded day is excluded from both numerator and denominator (Phase 0 follow-up).
- **Rationale:** ADR-0012 and review round 7 showed the median pre-filter excluded itineraries that connect. A bound test is exact in the direction that matters.
- **Alternatives:** no pre-filter (too many candidates at pool scale); median pre-filter (rejected by review).

## R3. Nonstop comparison

- **Decision:** the typical nonstop time for an origin/destination pair is the median scheduled elapsed time of all operated and cancelled nonstop flight-days on that pair, any airline, over the period. Each itinerary reports its median scheduled travel time over its connecting days, the nonstop median (or "none") and the ratio, rounded to 0.1.
- **Rationale:** a stable, easily explained reference. Medians over the connecting days match how travel time is reported elsewhere.

## R4. Curation

- **Decision:** a deterministic greedy selection over candidate routes, run after the analysis:
  1. Candidates are origin/destination pairs with at least two qualifying itineraries and at least one showcase comparison.
  2. Each route scores by its strongest cross-hub showcase difference (falling back to same-hub), with ties broken by number of showcase comparisons and then by route code.
  3. Routes are added in score order up to the configured maximum (12), keeping room for the regional quota (step 4); fewer than the minimum (8) is reported as a shortfall. The caps (at most one third of showcase comparisons from one route, at most half from one airline or hub) apply to the comparisons kept, not to route selection, because with few routes chosen any single route is necessarily a large share: each chosen route starts with its strongest comparison (cross-hub first, then the larger difference), and further comparisons are added in that order whenever the addition does not increase the total excess over the caps and under the cross-hub minimum (step 5). A comparison counts toward both itineraries' airlines and hubs. A comparison is added only while the route's compared itineraries stay within `itineraries_per_route_max`, so every compared itinerary fits in its route file. Caps still exceeded at the end are reported as shortfalls.
  4. At least half of the selected routes must have a regional origin (outside the candidate pool) when enough exist; otherwise the shortfall is reported.
  5. At least half of the showcase comparisons must be cross-hub (SC-002). The balancing in step 3 counts any shortfall against this minimum, so same-hub comparisons are added only while the share holds; if the seed comparisons alone fall short, the shortfall is reported with the share reached.
  6. The landing example is the highest-scoring cross-hub comparison whose lower itinerary is not tight and which was compared at every setting.
- **Rationale:** reproducible, explainable, and it enforces the balance requirements directly.
- **Alternatives:** hand-picked routes (not reproducible, not reviewable); optimization solver (opaque; unnecessary at this size).

## R5. Output files and size

- **Decision:** committed static JSON under `site-data/showcase/`:
  - `index.json`: coverage, routes, landing example, data period, definitions, manifest pointer;
  - `landing.json`: everything the landing view needs, loadable alone;
  - `routes/{ORIGIN}-{DEST}.json`: one per route, with its itineraries, comparisons, insights and daily data.

  Daily data is stored as compact columns (dates as day offsets from the period start, slack as integers, outcome as a one-letter code), not as one object per day. JSON is written with sorted keys, no extra whitespace and LF endings. The size budget is checked on gzip-compressed bytes and fails the run when exceeded.
- **Rationale:** per-route files let the explorer load only what it shows. Columnar arrays keep about 100 itineraries × 365 days well under the budget (estimated 0.5–1 MB compressed).
- **Alternatives:** one big file (slow first load); Parquet in the browser (heavier tooling for Phase 1).

## R6. Shape definitions and generated types

- **Decision:** Pydantic models in a new `flight_pipeline.showcase` package are the single definition (ADR-0007). A `schemas` command writes their JSON Schema to `shared/schemas/showcase.schema.json`. TypeScript types are generated from that schema with `json-schema-to-typescript` (exact version pinned, 15.0.4, run through `npx`; the schema is the serialization schema without field titles, so every field is required and types are inline), into `shared/types/showcase.ts`. Both are committed. CI regenerates them and fails on any difference.
- **Rationale:** ADR-0007 specifies JSON Schema in Phase 1. `json-schema-to-typescript` is the standard, maintained generator. A `shared/` directory sits outside both the pipeline and the future web app, so neither owns the contract.
- **Alternatives:** `pydantic-to-typescript` (wraps the same Node tool); hand-written types (forbidden by the constitution).

## R7. Shared test cases for the in-browser calculation

- **Decision:** `shared/test-cases/slack-feasibility.json` lists inputs (daily slack and outcomes, transfer time, cutoff) and expected outputs (feasible count, rate). The Python tests run them against the pipeline's calculation now; the explorer's tests will run the same file (constitution Principle II).

## R8. Faster alternatives (equivalence test)

- **Decision:** for each curated itinerary A, the candidates are the other qualifying itineraries B on the same origin and destination, departing within the departure window (3 hours), at least the minimum saving (15 minutes) shorter, with no travel-time tolerance. For each, the paired day-level bootstrap from Phase 0 (same seed scheme, 10,000 resamples) gives a 95% interval for rate(B) − rate(A). B is listed when the lower bound is at least −margin (2 points) and both have sufficient data on at least the minimum shared days. Listed alternatives are sorted by time saved, then by difference.
- **Rationale:** reuses the tested bootstrap. Equivalence by the interval's lower bound is the standard non-inferiority test.

## R9. Connecting options

- **Decision:** for each curated itinerary's inbound slot, the alternatives are the qualifying itineraries sharing that inbound slot and the destination (other outbound slots at the hub). They are ranked by rate, each with its sample. A better option is flagged when the paired interval for its difference excludes zero.

## R10. Buffer recommendation

- **Decision:** on each operated day, the scheduled layover that would just have met the threshold is `threshold + scheduled layover − actual slack`. The recommendation is the configured quantile (95%) of that value over operated days, using the lower discrete rule, rounded up to the next 5 minutes. Cancelled and diverted days are excluded, because no layover helps them, and that is stated.
- **Rationale:** direct, explainable, consistent with how slack is measured.

## R11. Monthly view

- **Decision:** a month's rate is shown when it has at least the configured monthly minimum of paired days (default 20); otherwise it says "insufficient data", or "no flights" when there were none. The overall minimum sample (30) stays for the itinerary rate.
- **Rationale:** months have about 30 days, so the overall minimum would hide most months. 20 days keeps one day at 5 points or less, consistent with whole-percent display.

## R12. Disruption notes

- **Decision:** `config/disruption_notes.toml` is a curated list: id, date range, airlines and/or airports, a one-line description and a public source URL. Notes are attached to a month when their date range overlaps it and the itinerary's airline or airports match. They are never used in any calculation. The file is pinned by checksum in the run manifest.

## R13. Schedule changes

- **Decision:** a schedule change is a date from which a slot's daily scheduled local departure time differs from its previous modal value by at least 10 minutes and stays at the new value for at least 7 consecutive scheduled days, plus every join of research R1 step 4 (whatever its length). Each change is reported with date, leg and old and new times. The connecting-day share comes from the daily matching (R2).

## R14. Deep-link parameters

- **Decision:** per itinerary: origin, destination, marketing airline(s), and for each leg the flight number used on most days with its share. The pipeline does not build URLs; the explorer builds them from these fields, so URL formats can change without rerunning the pipeline.

## R15. Reproducing Phase 0

- **Decision:** Phase 0's results are frozen. A git tag `phase0-final` marks the commit that produced `reports/phase0/`; `verify` with `config/phase0.toml` on that tag reproduces them. Phase 1 uses a new `config/phase1.toml` and writes to new output locations; the code may change behaviour that Phase 0 relied on.
- **Rationale:** keeping both behaviours in one codebase would double the rules and tests for an analysis that is already decided.
- **Alternatives:** an identity-mode flag (adds a permanent second code path).

## R16. Performance

- **Decision:** estimates on the 16-core development machine. Phase 0 took 7.9 minutes. Slot building is one sort per (airline, origin, destination). The bound pre-filter keeps the daily matching close to Phase 0's sold-candidate volume (about 50,000–80,000 itineraries × 365 days). Curation and insights run only on the curated routes. Expected total: 10–15 minutes there, within 30 minutes on the 4-core reference machine; `run` records the runtime as before.
- **Measured (T048):** the first real run took 146 minutes: the daily matching of every candidate through 30 pool airports (hub selection) and 7 hubs (build), 54.5 million matched days validated row by row, and insights loading whole tables as models. Changes, none of which alters any output (every derived and published file is byte-identical before and after): the matching runs one hub at a time, as separate statements (DuckDB plans the fused query far worse on large hubs) and, where only per-itinerary results are needed, on integer keys; `itinerary_days.parquet` holds the selected pairs only, rebuilt for them and checked against the full build; slot instances cover only the candidates' slots; flight instances are built once for all scenarios; insights read only the rows they need; model rows are inserted in batches; and paired bootstraps run in parallel processes (each has its own seeded stream). With DuckDB and the bootstrap workers limited to 4 (`FLIGHT_PIPELINE_THREADS=4`), the full run takes 28.4 minutes excluding downloads.
