# Implementation Plan: Explorer Core

**Branch**: `004-explorer-core` | **Date**: 2026-11-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-explorer-core/spec.md`

**Approval**: the owner instructed on 2026-11-28 that the remaining Phase 1 work proceed with recommended decisions, stopping only when blocked or at the end of the phase. That instruction stands as approval of this spec and plan (constitution, Development Workflow). The merge decision stays with the owner.

## Summary

**Data contract (pipeline).** The pipeline publishes two additive contract fields: `index.airports` (code, name, city and coordinates from airportsdata) and four schedule fields per itinerary (the median hub arrival and hub departure, and each flight's scheduled duration). It does this with the existing `publish` stage, schema 1.1.0.

**Explorer (web).** The web app gains:
- a route picker;
- a list of itinerary cards in departure order;
- a timeline of flight, layover and flight bars;
- a MapLibre map of curved paths through the hubs, loaded after the first view;
- a detail panel.

All views read and write one selection held in the address (`route`, `itinerary`; ADR-0010). Route files load on demand through the existing data-access module, with the same validation and cross-checks as the landing file.

## Technical Context

**Language/Version**: TypeScript strict on Node 24 (web); Python 3.13 (pipeline addition).

**Primary Dependencies**:
- `maplibre-gl` 5.24.1 with `@vis.gl/react-maplibre` 8.1.3 (react-map-gl's MapLibre package; ADR-0002);
- `@turf/great-circle` 7.4.0 for the curved paths (ADR-0002);
- no router library: the selection is two query parameters read and written with the History API.

**Storage**: none. Static JSON as in feature 003; route files fetched when first shown.

**Testing**: as in feature 003. In addition:
- map e2e tests read rendered features through the map instance, exposed only to tests;
- the basemap style is replaced by a local blank style in every test, by route interception (FR-016).

**Target Platform / Project Type**: unchanged (static site on GitHub Pages).

**Performance Goals**:
- first-view scripts at most 150 KB gzip;
- the lazily loaded map scripts at most 300 KB gzip (MapLibre 5.24.1 with its built-in worker measures 273 KB);
- Lighthouse mobile performance at least 0.90 and accessibility 1.00 on the default view;
- the largest route file at most 150 KB gzip (it is about 25 KB today).

**Constraints**: no network in tests; no time-zone arithmetic in the browser; selection never shown by color alone.

**Scale/Scope**: 12 routes, up to 12 itineraries each; 19 airports.

## Constitution Check

| Principle | Status | How |
|---|---|---|
| I. Statistical honesty | Pass | The cards and detail reuse feature 003's rate text, definitions and insufficient-data rule. Lists are ordered by departure time, never by rate. The new data fields are schedule facts with their definitions |
| II. Automated verification | Pass | Pipeline additions written test-first (done: model and slot-time tests). Map geometry, timeline layout, ordering and URL parsing are pure, unit-tested functions. Map e2e tests assert rendered features. Visual references cover each view at 360 and 1280 px. axe and keyboard tests cover the new controls |
| III. Thin slices | Pass | Deployable on its own; out of scope listed; README and architecture updated |
| IV. One data contract | Pass | The additions are Pydantic fields, with the schema and types regenerated (1.1.0). The browser formats published local minutes only |
| V. Accessible and clear | Pass | Text equivalents for the map and timeline; keyboard selection in the list and timeline; phone stacking with a map toggle; budgets set (FR-017) |
| VI. Simplicity, providers | Pass | No router or state library: the address is the state. The basemap style URL is configuration, so a self-hosted style can replace OpenFreeMap without code changes |
| ADRs | Pass | ADR-0002's map choices (MapLibre, react-map-gl, Turf) are used. ADR-0010's URL state is implemented. ADR-0016's plain CSS is kept. No new ADR is needed |
| Licences | Pass | Basemap attribution (OpenFreeMap, OpenMapTiles, OpenStreetMap contributors) is always visible; airportsdata is already attributed |

## Project Structure

```text
pipeline/src/flight_pipeline/
├── providers/airports.py      # airport_infos (airportsdata)
└── showcase/                  # models: AirportInfo, Schedule additions; assemble: slot_times

web/src/
├── selection/                 # parse and serialize ?route=&itinerary=, fallback, history (pure + hook)
├── explorer/                  # Explorer, RoutePicker, ItineraryList, Timeline, DetailPanel, MapPanel
├── map/                       # geometry.ts (pure: paths, bounds, labels), MapView.tsx (lazy chunk)
├── data/                      # + useRoute(routeId), buildRouteView cross-checks
└── format/                    # + departure order, timeline layout
web/tests/
├── unit/                      # selection, ordering, timeline layout, map geometry, route cross-checks
├── component/                 # explorer selection sync, fallback note
├── e2e/                       # every route, selection from each view, links, back/forward, map features
├── visual/  a11y/  keyboard/  # new views
└── fixtures/blank-style.json  # local basemap style for tests
```

## Delivery Order

1. Pipeline contract additions. Done in commit c72cf16, with the verification run recorded.
2. **Foundation:** selection parsing, departure ordering, timeline layout, route loading and cross-checks, all test-first.
3. **US1:** route picker, list, timeline, detail panel, then the lazy map.
4. **US2:** URL state, history and fallback.
5. **US3:** phone layout, map toggle, text equivalents, then accessibility and keyboard tests.
6. **Polish:** budgets, visual references, docs, validation and independent review.

## Complexity Tracking

| Addition | Why needed | Simpler alternative rejected because |
|---|---|---|
| Visual references mask the map area | Under the software renderer, the map can shift by a pixel between runs, so exact screenshots of it flake | The map is checked through its rendered features instead, which is what the constitution asks of map tests (Principle II). The rest of each page is compared exactly |
| A second script budget for a lazily loaded map chunk | MapLibre is about 275 KB gzip, above the 150 KB first-view budget | Loading it in the first view would break SC-004. A static map image would not support selection or rendered-feature tests |
