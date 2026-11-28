# Feature Specification: Explorer Core

**Feature Branch**: `004-explorer-core`

**Created**: 2026-11-28

**Status**: Draft

**Input**: User description: "Phase 1 feature explorer-core from docs/roadmap.md: map, list and timeline with synced selection; selection in the URL. Deployable on its own." The owner asked for the remaining Phase 1 work to proceed with recommended decisions.

## Context

The web foundation (feature 003) put one real comparison online, with the checks every later feature relies on. This feature turns that page into an explorer of all 12 curated showcase routes. A visitor picks a route and sees its one-stop itineraries three ways at once:
- on a map, as curved routes through each hub;
- in a list of itinerary cards;
- on a timeline of each itinerary's two flights and layover.

Selecting an itinerary in any view selects it in all three, and the selection lives in the address so any view can be linked ([ADR-0010](../../docs/adr/0010-url-selection-state.md)). The risk visuals, transfer-time slider and insight panels follow in `explorer-insights`.

The published data has no airport coordinates or hub times, which the map and timeline need. This feature therefore adds two small, additive fields to the data contract, produced by the pipeline from data it already has.

## Clarifications

### Session 2026-11-28

The owner asked for recommended decisions to be adopted directly. Each answer below is the recommended option.

- Q: In what order are a route's itineraries listed? → A: By scheduled departure time, earliest first. Ordering by rate would rank every itinerary, including those below the minimum sample (constitution, Principle I). Departure order is neutral and matches how travelers scan schedules.
- Q: What does the page show before an itinerary is selected? → A: On the landing route, the landing comparison from feature 003, unchanged. On any other route, the route's itineraries with none selected, and a prompt to select one. The default address opens on the landing route.
- Q: What does the timeline's horizontal axis show? → A: Hours after the first departure in the origin's local time. Each itinerary is a bar from its departure: the inbound flight, the layover at the hub, then the outbound flight, sized by their scheduled durations. Each end is labelled with its own airport's local time, so no time-zone arithmetic happens in the browser.
- Q: How does the map stay within the page's performance budget? → A: The map library is loaded only after the first view has rendered. List and timeline work without it. The script budget is split into a first-view budget (unchanged, 150 KB gzip) and a map budget.
- Q: Where do basemap tiles come from, and what do tests use? → A: A free hosted vector style with no key (OpenFreeMap), with its attribution always visible. Tests replace the style with a local blank style, so they make no network requests and render identically everywhere.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Explore any showcase route in three linked views (Priority: P1)

A visitor picks one of the 12 showcase routes. The page shows the route's itineraries three ways:
- **On the map:** origin, destination and hubs, with a curved line from the origin through each hub to the destination.
- **In a list of cards:** each with airline and hub, flight numbers, local departure and arrival, layover, and "worked on X% of N days" or "insufficient data".
- **On a timeline:** each itinerary's inbound flight, layover and outbound flight drawn to scale.

Selecting an itinerary in the list, on the map or on the timeline highlights it in all three. Its details appear in a panel with the same figures and definitions as the landing page.

**Why this priority**: this is the explorer the roadmap promises. Seeing the same itineraries as geography, as a list and in time is what makes the comparison understandable at a glance.

**Independent Test**: open each route. The list, map and timeline show the same itineraries, matching the route file. Selecting from each view updates the other two, and the details match the data.

**Acceptance Scenarios**:

1. **Given** the explorer, **When** a visitor chooses a route from the route picker, **Then** the list, map and timeline show exactly that route's itineraries, and no others.
2. **Given** a route, **When** the list is shown, **Then** itineraries are ordered by scheduled departure time. Each card shows airline and hub, flight numbers, local departure and arrival with "+1 day" where needed, layover, and the rate with its days and period, or "insufficient data". A "Tight layover" badge with text appears where the data marks the layover tight.
3. **Given** a route, **When** the map is shown, **Then** each hub has a labelled outlined circle, origin and destination are labelled, and each itinerary's path runs from origin through its hub to destination as a curved line. The selected path is thicker and solid; others are thin and dashed, so selection is not shown by color alone.
4. **Given** a route, **When** the timeline is shown, **Then** each itinerary has a bar with its inbound flight, layover and outbound flight sized by scheduled minutes. Each end is labelled with its local time, and the bars share one axis of hours after the route's earliest departure.
5. **Given** an itinerary selected in any one view, **When** the selection changes, **Then** the other two views show the same selection within the same frame, and the detail panel shows that itinerary.
6. **Given** a selected itinerary, **When** its details are shown, **Then** every figure has its definition, sample size and data period, as on the landing page (constitution, Principle I).

---

### User Story 2 - Every view has a link (Priority: P1)

A visitor or the project owner copies the address while looking at a route and itinerary, and sends it. Opening it shows the same route and selection. The back and forward buttons move between selections. A broken or outdated link opens the default view with a short note, never an error page.

**Why this priority**: links to specific examples are how the project is shared from a CV or README (ADR-0010). Without them the explorer cannot be pointed at.

**Independent Test**: for each route, open an address with that route and a selected itinerary. The same view appears. Change the selection, go back, and the previous selection returns. Open addresses with an unknown route or itinerary and get the default view with the note.

**Acceptance Scenarios**:

1. **Given** an address naming a route and an itinerary, **When** it is opened, **Then** that route is shown with that itinerary selected in all views.
2. **Given** a selection change, **When** the visitor presses back, **Then** the previous selection is shown. Choosing a route or itinerary adds one history entry.
3. **Given** an address with an unknown route, or an itinerary not on the route, **When** it is opened, **Then** the default view opens with a note that the linked example was not found. The address is corrected without adding a history entry.
4. **Given** the default address with no parameters, **When** it is opened, **Then** the landing route and the landing comparison appear, as today.

---

### User Story 3 - Works by keyboard, with assistive technology and on phones (Priority: P2)

A keyboard or screen-reader user reaches the route picker, every itinerary and every control. Selection is announced, and the map and timeline have text equivalents. On a phone the views stack: the list comes first, the map can be shown or hidden, and the selected itinerary expands in place.

**Why this priority**: constitution Principle V. Reviewers often open the demo on a phone. The map is the hardest part to make accessible, so it needs explicit equivalents.

**Independent Test**: complete Story 1 with the keyboard alone, and with a screen reader's view of the page. Repeat at 360 px wide.

**Acceptance Scenarios**:

1. **Given** the keyboard only, **When** a visitor uses Tab, Enter and Space, **Then** they can pick a route, select any itinerary from the list or the timeline, and reach the details, with visible focus throughout.
2. **Given** a screen reader, **When** an itinerary is selected, **Then** the selection is announced. The map has a text description listing the route's airports and paths, and each timeline bar has a label with its times and durations.
3. **Given** a 360 px screen, **When** the page loads, **Then** it has no horizontal scroll. The list comes before the map, and the map can be shown and hidden with a labelled button.
4. **Given** any state, **When** automated accessibility checks run, **Then** there are no WCAG 2.2 AA violations.

### Edge Cases

- **Route file missing or malformed:** that route shows the plain error message, and other routes still work.
- **No basemap:** the basemap style or tiles fail to load. Routes, airports and labels still draw on a plain background.
- **Map library fails to load:** the list and timeline still work, and the map area says the map could not be shown.
- **Insufficient data:** an itinerary below the minimum sample appears in all views with "insufficient data". It is never placed above or below others by its rate.
- **Arrival after midnight:** the timeline bar extends past 24 hours and the arrival label says "+1 day".
- **Several itineraries through one hub:** their paths overlap on the map. Selecting one draws it above the others, and the list and timeline still distinguish them.
- **Very long route names or many itineraries:** the list scrolls with the page, with no nested scroll trap. The busiest route has 12 itineraries.

## Requirements *(mandatory)*

### Functional Requirements

**Data contract (pipeline)**

- **FR-001**: The showcase index MUST list every airport that appears in the showcase (origins, destinations and hubs). Each entry has its code, name, city, latitude and longitude, from the attributed airport data source the pipeline already uses.
- **FR-002**: Each itinerary's schedule MUST add:
  - the median scheduled local arrival at the hub and the median scheduled local departure from the hub;
  - the median scheduled duration of each of its two flights.

  All are computed over the same days as the existing schedule fields, from data the pipeline already has.
- **FR-003**: Both additions MUST be part of the generated data contract (schema and types), published by the existing pipeline. They MUST be reproduced by its verification. No existing field or figure changes.

**Explorer**

- **FR-004**: A route picker MUST list the 12 showcase routes by origin and destination, with airport names. It is reachable by keyboard and labelled.
- **FR-005**: The list MUST show the route's itineraries in scheduled-departure order, with the card content of User Story 1, scenario 2. Each card is one control that selects the itinerary, and shows its selected state by border, weight and text, not by color alone.
- **FR-006**: The map MUST show the route's airports and the itineraries' paths, as in User Story 1, scenario 3. Path geometry and label placement are computed by pure, unit-tested functions. Paths are selectable by pointer. The basemap's attribution is always visible.
- **FR-007**: The timeline MUST show each itinerary as in User Story 1, scenario 4. Each bar is a keyboard-operable control with a text label giving its local times and durations.
- **FR-008**: The selection (route and itinerary) MUST be held only in the address. The list, map, timeline and detail panel MUST read it from there and write to it on interaction (ADR-0010). Parameter names are `route` and `itinerary`.
- **FR-009**: The detail panel MUST show the selected itinerary with every figure's definition, sample and period, reusing the landing page's itinerary card and definitions. On the landing route with no itinerary selected, it shows the landing comparison.
- **FR-010**: Unknown or outdated parameters MUST fall back to the default view with a short note, replacing the address without a new history entry.
- **FR-011**: Route files MUST load only through the data-access module, when their route is first shown, and MUST be validated and cross-checked like the landing file. A failed route shows the plain error for that route only.
- **FR-012**: The map library MUST load only after the first view has rendered. If it fails, the list and timeline keep working and the map area says so.
- **FR-013**: On screens narrower than 768 px, the views MUST stack in the order route picker, list, timeline, map, with the map hidden by default behind a labelled show/hide button.
- **FR-014**: The page MUST follow docs/design.md: tokens, typography, focus, 44 px targets, reduced motion with no animated transitions, and never color alone.

**Checks**

- **FR-015**: The checks of feature 003 MUST cover the new views:
  - unit tests for every pure function (ordering, timeline geometry, map geometry, URL parsing and fallback);
  - component tests for selection sync;
  - end-to-end tests that assert rendered map features, not only pixels (constitution, Principle II);
  - visual references for each view at phone and desktop sizes;
  - axe and keyboard tests for the new controls.
- **FR-016**: Tests MUST NOT use the network. The basemap style is replaced by a local blank style in every test.
- **FR-017**: The budgets MUST be updated in the same change and enforced:
  - first-view scripts at most 150 KB gzip;
  - map scripts at most 300 KB gzip, loaded after the first view;
  - the largest route file at most 150 KB gzip;
  - Lighthouse mobile performance at least 0.90 and accessibility 1.00 on the default view.

### Key Entities

- **Airport**: code, name, city, latitude and longitude. One entry for each airport that appears in the showcase.
- **Schedule additions**: per itinerary, the median scheduled hub arrival and hub departure (local minutes), and the inbound and outbound flight durations (minutes).
- **Selection**: route and itinerary, held in the address.
- **Route view**: one route's itineraries, comparisons and period, loaded on demand through the data-access module.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 12 showcase routes open in the explorer. For each, the list, map and timeline show the same itineraries as its route file, checked automatically.
- **SC-002**: Selecting from any of the three views updates the other two and the detail panel for 100% of itineraries on every route, checked automatically.
- **SC-003**: Every address with a valid route and itinerary reopens the same view. Every invalid address opens the default view with the note. Both are checked for all routes.
- **SC-004**: The default view keeps Lighthouse mobile performance at least 0.90 and accessibility 1.00. First-view scripts stay at most 150 KB gzip, and map scripts at most 300 KB gzip.
- **SC-005**: Zero automated accessibility violations (WCAG 2.2 AA) at phone and desktop sizes, for the default view and a route with a selection. Every control is reached and operated by keyboard in the scripted tests.
- **SC-006**: The data-contract additions are reproduced exactly by the pipeline's verification run, and the existing published figures are unchanged.

## Out of Scope

- Risk visuals (reliability meter, failure bar, month chart), the transfer-time slider, the traveler-insight panels, "Find this itinerary" links, and the "How the numbers work" page (`explorer-insights`).
- Search for routes beyond the 12 showcase routes, the paste box and an API (Phase 2).
- Changes to how any figure is computed. The pipeline only publishes two kinds of existing values it did not publish before.
- City-level map styling, 3D, animation of routes, and offline tiles.

## Assumptions

- **Tools:** the map uses MapLibre GL JS through `react-map-gl`, with Turf.js only if great-circle helpers are needed (ADR-0002). The planning step checks their sizes against the map budget.
- **Basemap:** OpenFreeMap's hosted styles, free with no key, with attribution to OpenFreeMap, OpenMapTiles and OpenStreetMap contributors. If its terms do not fit, a self-hosted Protomaps file is the ADR-0002 alternative.
- **Airport names and cities:** come from `airportsdata`, already used and attributed for time zones.
- **Tests:** WebGL renders in the pinned Playwright image through its software renderer, so map screenshots are deterministic there.
- **Data:** the existing showcase files and pipeline are the inputs. The rerun to publish the additions follows the pipeline's verified process.
