# Research: Explorer Core

## R1. Map library and loading

**Decision:** `maplibre-gl` 5.24.1 through `@vis.gl/react-maplibre` 8.1.3, imported with `React.lazy` after the first view renders. The style URL comes from configuration (`VITE_BASEMAP_STYLE`), and defaults to OpenFreeMap's `positron` style.

**Rationale:** these are ADR-0002's choices. Lazy loading keeps the first view within its 150 KB budget, and the list and timeline don't depend on the map.

**Why 5.24.1, not 6:** MapLibre 6 ships its main code and its web worker as separate ES modules, and starts the worker from a URL inside the dependency. With Vite, the worker either failed to load or, once bundled separately, never completed the map's `load`. That also put the map at about 450 KB gzip. MapLibre 5.24.1 (released 2026-11-11) ships one bundle with the worker built in, works with Vite unchanged, and is 273 KB gzip. Revisit 6 when its bundler integration settles.

**Alternatives:**
- **A static SVG map with a projection library:** smaller, but no basemap context, and it would break with ADR-0002.
- **deck.gl:** on ADR-0002's avoid list.

## R2. Curved paths

**Decision:** each path is two great-circle arcs (origin to hub, hub to destination), from `@turf/great-circle` with 32 points per arc. They are computed in a pure function, `routePaths(airports, itineraries)`, that returns GeoJSON with each itinerary's id and hub. Itineraries through the same hub share geometry, so overlapping paths are told apart by selection (thicker and solid) and by the list and timeline.

**Rationale:** ADR-0002 (Turf) and design.md ("curved great-circle-style route lines through each hub"). A pure function is unit-tested (constitution, Principle II).

## R3. Selection in the address

**Decision:**
- **Parameters:** `?route=LIT-LGA&itinerary=<itinerary_id>`, with the itinerary id URL-encoded.
- **Pure functions:** `parseSelection(search, index)` returns the selection plus a fallback note; `serializeSelection`.
- **Hook:** `useSelection()` subscribes to `popstate`, writes with `pushState` on user choices and `replaceState` on corrections.
- **No router library.**

**Rationale:** ADR-0010. Two parameters don't justify a router (ADR-0016's simplicity).

## R4. Timeline

**Decision:**
- **Axis:** minutes after the route's earliest departure, on the origin's local clock (all itineraries on a route share the origin).
- **Bars:** each itinerary is a bar starting at its departure, with three segments sized by `inbound_min`, `layover_min` and the remainder of `travel_min`, so the total equals the published travel time.
- **Labels:** the ends are labelled with departure and arrival in their own local times.
- **Layout:** a pure function, `timelineRows(itineraries)`, returns rows with segment offsets and widths in minutes, and the axis extent. It is rendered as SVG inside a list of buttons, one per itinerary, with a text label.

**Rationale:**
- **Honest:** every length is a published duration, and no time-zone arithmetic is needed.
- **Accessible:** the buttons and labels give a text equivalent.

## R5. Basemap in tests

**Decision:** the Playwright fixture intercepts the style URL and serves `tests/fixtures/blank-style.json`, a style with only a background layer, no sources and no glyphs. Labels for airports are HTML markers, not map symbols, so they need no glyph server.

**Rationale:** no network in tests (FR-016), and deterministic screenshots in the pinned image.

## R6. Map assertions

**Decision:** in test builds only (`import.meta.env.MODE === "test"`, or the `?test` flag the e2e fixture sets), the map instance is exposed as `window.__travelCheckMap`. Tests call `queryRenderedFeatures` on the path layers and assert the itinerary ids drawn and which one is selected (constitution, Principle II: assert rendered features).

## R7. Budgets

**Decision:**
- first-view JS at most 150 KB gzip;
- the map scripts at most 300 KB gzip (size-limit with two entries; MapLibre 5.24.1 with its built-in worker measures 273 KB);
- the largest route file at most 150 KB gzip (check-data-size extended);
- the Lighthouse thresholds unchanged.

**Rationale:** spec FR-017.
