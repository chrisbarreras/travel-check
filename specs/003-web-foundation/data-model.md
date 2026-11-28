# Data Model: Web Foundation

This feature defines no new data shapes. Every shape it reads comes from the generated contract: `shared/schemas/showcase.schema.json` and `shared/types/showcase.ts`, from the Pydantic models of feature 002. That document stays canonical: see [feature 002's data model](../002-showcase-data-pipeline/data-model.md) and [outputs contract](../002-showcase-data-pipeline/contracts/outputs.md). This document records what the page reads from that contract, the display rules applied to it, and the web-side types that exist only in the browser.

## Files read by the first view

| File | Contract type | Used for |
|---|---|---|
| `data/showcase/index.json` | `ShowcaseIndex` | `landing` (which comparison to show), `period`, `definitions`, `attribution` |
| `data/showcase/landing.json` | `RouteFile` (restricted to the landing comparison and its two itineraries) | The comparison and both itineraries |
| `data/showcase/manifest.json` | `ShowcaseManifest` | `run.run_at`, shown as the date the data was built |

These total about 9 KB gzip today, against a 150 KB budget (SC-002). Route files are loadable through `getRoute`, but no screen uses them in this feature.

## Fields shown, and their display rules

| Shown as | Contract field | Rule |
|---|---|---|
| Route | `RouteFile.route_id`, and each itinerary's `find.origin` and `find.dest` | Airport codes; the contract has no city names |
| Hub | `ShowcaseItinerary.hub` | Airport code |
| Airline | `ShowcaseItinerary.airline`, `airline_out` | Display name from a small web-side table (below); when the two differ, both are named. The code is shown when a name is missing |
| Flight numbers | `ShowcaseItinerary.find.legs[].flight_number` with `share_of_days` | The leg's most frequent flight number, with "on N% of days" when below 95%. Schedule-slot itineraries can fly under several numbers (ADR-0014) |
| Scheduled times | `Schedule.dep_local_min`, `arr_local_min`, `travel_min` | Minutes after local midnight at each airport (0–1439), shown as "12:38 pm" and labelled "local time". "+1 day" when the arrival falls on a later local day. That is found from the departure clock time plus `travel_min`, against the arrival clock time, taking the two airports' clock difference within ±12 hours. No time-zone data is used |
| Layover, travel time | `Schedule.layover_min`, `travel_min` | "1 h 39 min" |
| Worked on | `Rate.rate`, `Rate.paired_days`, `Rate.count_feasible`, `Rate.status` | `ok`: whole percent, rounded halves away from zero, with "of N days" (N = `paired_days`). `insufficient_data`: "insufficient data (N days)", no percentage |
| Not counted | `ShowcaseItinerary.excluded_days` (`not_connecting`, `end_of_period`, `quality`) | Each non-zero count with its reason, for example "11 days the flights didn't connect on schedule" |
| Difference | `ShowcaseComparison.difference`, `ci_low`, `ci_high`, `shared_days` | Whole points with a sign. The interval as "95% interval +22 to +35 points", with "over 242 days both flew". `itinerary_a` is the higher rate |
| Similar or more often | `ci_low`, `ci_high` (exact) | `ci_low > 0`: "worked more often"; otherwise "worked on a similar share of days". Decided on stored values, never on rounded ones |
| Period | `DataPeriod.start`, `end` | "Jul 2024 – Jun 2025" |
| Definitions | `ShowcaseIndex.definitions[]` by `key` (`connection_feasibility`, `paired_days`, `comparison_difference`, `layover`, `travel_time`) | Text shown verbatim, with a link to `methodology_anchor` in the repository |
| Attribution | `ShowcaseIndex.attribution[]` | `text` with its `url` and `licence`, verbatim |
| Data built | `ShowcaseManifest.run.run_at` | Date only, for example "Built 26 Nov 2026" |

## Web-side types (browser only)

These are TypeScript types in `web/src/data/`, not data contracts: they never leave the browser and are not published.

- **DataSource:** the provider interface. It has `getIndex()`, `getLanding()`, `getRoute(routeId)` and `getManifest()`. Each returns `Promise<Result<T>>`.
- **Result<T>:** either `{ ok: true, value: T }` or `{ ok: false, error: DataError }`.
- **DataError:** `{ kind: "network" | "not_found" | "invalid", file: string, detail: string }`.
  - `invalid` carries the first validation messages, for the console and tests only; visitors see the plain message.
  - A malformed file is rejected as a whole (FR-012).
- **LandingView:** the validated, cross-checked pair that screens render: index, landing file, the landing comparison, its two itineraries in order (a, then b) and the manifest. Building it fails as `invalid` when the comparison or either itinerary is missing.
- **Airline names:** a constant map from airline code to display name, for example `DL` → "Delta", for every carrier that can appear in the showcase. A unit test checks that every airline code in the committed showcase files has a name. A missing name falls back to the code and is never a hard failure.

## State

The page has three states: **loading** (layout shape, no numbers), **ready** (the LandingView) and **error** (plain message, no figures). There is no other client-side state and nothing is stored in the browser.
