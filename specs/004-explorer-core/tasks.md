---
description: "Task list for the explorer core"
---

# Tasks: Explorer Core

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md)

**Tests**: required.
- Pure functions and pipeline code are written test-first.
- Components ship with their tests.
- Map tests assert rendered features (constitution, Principle II).

## Phase 1: Data contract (pipeline)

- [X] T001 Write the failing model tests for `AirportInfo` and the `Schedule` additions in pipeline/tests/unit/test_showcase_models.py, and the slot-time and airport tests in pipeline/tests/unit/test_explorer_data.py (FR-001, FR-002)
- [X] T002 Implement `AirportInfo`, `ShowcaseIndex.airports` (sorted, unique, covering route airports), the `Schedule` hub times and flight durations (flights within travel time), `providers/airports.py`, `assemble.slot_times`, and schema 1.1.0
- [X] T003 Republish the showcase data and regenerate the schema and types. Commit them (c72cf16)
- [X] T004 Run the full pipeline test suite, `schemas --check` and `verify`, and record the result in specs/004-explorer-core/validation.md (FR-003, SC-006)

## Phase 2: Foundation (web)

- [X] T005 [P] Add `maplibre-gl`, `@vis.gl/react-maplibre` and `@turf/great-circle` at the pinned versions; add the second size-limit entry and the route-file budget (FR-017)
- [X] T006 [P] Test-first: web/src/selection/ with `parseSelection` and `serializeSelection` (route and itinerary parameters, fallback note, landing default) and the `useSelection` hook (push on choice, replace on correction, popstate) (FR-008, FR-010)
- [X] T007 [P] Test-first: `byDeparture` ordering and `timelineRows` layout in web/src/format/ (FR-005, FR-007)
- [X] T008 [P] Test-first: `routePaths`, `airportPoints` and `bounds` in web/src/map/geometry.ts (FR-006)
- [X] T009 Test-first: `useRoute(routeId)` in web/src/data/, with `buildRouteView` cross-checks (rate against counts, minimum sample, ordered comparisons, airports present in the index) (FR-011)

## Phase 3: US1, explore any showcase route in three linked views (P1)

- [X] T010 [US1] Add RoutePicker, ItineraryList (cards as buttons with `aria-pressed`, tight-layover badge) and DetailPanel (reusing ItineraryCard and the definitions), with component tests for selection sync (FR-004, FR-005, FR-009)
- [X] T011 [US1] Add the Timeline (SVG bars inside one labelled button per itinerary) with a component test (FR-007)
- [X] T012 [US1] Add the lazily loaded MapView: airports as HTML markers, paths as a GeoJSON line layer (selected solid and thick, others dashed), click to select, attribution, and a test-only map handle (FR-006, FR-012)
- [X] T013 [US1] Add the e2e tests: for every route, the list, timeline and map features match the route file; selecting from each view updates the others (SC-001, SC-002)

## Phase 4: US2, every view has a link (P1)

- [X] T014 [US2] Wire the selection hook into the explorer, with the landing default and the fallback note. E2e tests: every route and itinerary reopens from its address; back and forward; invalid addresses (FR-008, FR-010, SC-003)

## Phase 5: US3, keyboard, assistive technology and phones (P2)

- [X] T015 [US3] Phone layout (stacked order; map hidden behind a labelled toggle), map text description, and a live region announcing the selection (FR-013, FR-014)
- [X] T016 [US3] Extend the axe and keyboard tests to the explorer (route picker, list, timeline, toggle), and the visual references for each view at 360 and 1280 px (SC-005)

## Phase 6: Polish

- [X] T017 Budgets and Lighthouse on the default view; README and docs/architecture.md; specs/004-explorer-core/validation.md (SC-004). The roadmap row is marked complete at merge, as for feature 003
- [X] T018 Independent review: a new `feature-reviewer` per round, given only `specs/004-explorer-core` and `main`, until APPROVE; save the rounds as review.md
