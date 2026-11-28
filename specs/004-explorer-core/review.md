# Independent review: Explorer Core

Each round is a new `feature-reviewer` agent, given only `specs/004-explorer-core` and the base branch `main` (constitution, Development Workflow).

## Round 1 (main...053ffd9)

**Verdict:** CHANGES REQUIRED. 3 blocking, 7 should-fix, 3 nits.

**Automated checks, all passing:**
- **Pipeline:** ruff, format and pyright; 543 tests; `schemas --check`.
- **Web:** format, lint and typecheck; 162 unit and component tests; build; size; 57 browser tests (local).

### Findings and responses

| # | Severity | Finding | Response |
|---|---|---|---|
| 1 | BLOCKING | The hub times and flight durations were medians over every day each slot flew, not the itinerary's connecting days (FR-002). They disagreed with `layover_min` for 106 of 144 itineraries, and with `travel_min` for 126. | **Fixed.** The hub arrival and inbound duration are medians over the itinerary's connecting days (`assemble.hub_times`, from `itinerary_days`). The hub departure is that arrival plus the median layover, and the outbound duration is the travel time less inbound and layover. The model enforces both rules, so all 144 agree. A `flight_times` definition and a methodology section explain this. The data was republished and `verify` rerun (recorded in validation.md). |
| 2 | BLOCKING | The timeline showed no local times; they were only in `aria-label`. | **Fixed.** Every bar shows "12:38 pm LIT → 3:13 pm–4:52 pm ATL → 7:13 pm LGA", with "+1 day" where the arrival falls on a later local day. It also has a "How these times are found" definition. The button's accessible name is its visible text plus the durations. |
| 3 | BLOCKING | An itinerary not on the route kept the route instead of opening the default view (US2-3, FR-010). | **Fixed.** It now opens the default view with the not-found note, and the address is corrected without a history entry. The unit, component and e2e tests are updated to the spec's behaviour, and validation.md is corrected. |
| 4 | SHOULD-FIX | The timeline announced an outbound time derived from the others, not the published one. | **Fixed.** The timeline uses the published `outbound_min`, which now agrees by construction. |
| 5 | SHOULD-FIX | No test covered FR-010's history behaviour. | **Fixed.** A component test spies on `pushState`: one per choice, none for repeats, none for fallback corrections, one for consecutive route changes. |
| 6 | SHOULD-FIX | One bad route file was untested. | **Fixed.** A component test corrupts `routes/MCO-LAS.json`. That route shows the error, and switching routes clears it. |
| 7 | SHOULD-FIX | SC-002 was claimed for every itinerary but tested on one route. | **Fixed.** An e2e test selects all 144 itineraries on the 12 routes from the list, and checks the timeline and the map's rendered selected layer for each. |
| 8 | SHOULD-FIX | The tests' basemap and research R1/R5 didn't match FR-016. | **Fixed.** The fixture serves `tests/fixtures/blank-style.json`. One test uses the real style with tiles blocked, for the "no basemap" case. R1 and R5 describe the local style. |
| 9 | SHOULD-FIX | The visual references didn't cover each view at both sizes; the map masking was unrecorded. | **Fixed.** Added a selected itinerary at 360 px and a route with nothing selected at 1280 px (8 references). The map masking is recorded in the plan's Complexity Tracking: the map is tested through rendered features. |
| 10 | SHOULD-FIX | The methodology and attribution didn't cover the new airportsdata uses or the new fields. | **Fixed.** The attribution reads "Airport names, cities, locations and time zones from the airportsdata package". methodology.md lists the new uses and has a "Flight times on the timeline" section. The `flight_times` definition is published and shown. |
| 11 | NIT | Re-selecting the selected itinerary added a history entry. | **Fixed.** No write when the selection is unchanged. |
| 12 | NIT | Arrow keys in the route picker added an entry per keypress. | **Fixed.** Consecutive route-picker changes replace one entry. |
| 13 | NIT | The index validator didn't require hub airports. | **Answered.** The index doesn't list hubs (route summaries have only origin and destination), so the model can't check them. `assemble.index_of` includes every hub, and the web's `buildRouteView` rejects a route whose hub is missing from `airports`, as a unit test shows. |
