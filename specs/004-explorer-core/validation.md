# Validation: Explorer Core

Results on 2026-11-28 for the success criteria in [spec.md](spec.md). Local runs used Windows 11 with Docker Desktop; CI runs used GitHub-hosted `ubuntu-latest` runners.

| Criterion | Result |
|---|---|
| SC-001: every route in all three views | Pass. `tests/e2e/explorer.spec.ts` opens each of the 12 routes. The list and timeline order, and the map's rendered path features (read with `queryRenderedFeatures`), equal the route file's itineraries in departure order |
| SC-002: selection shared by every view | Pass. For all 144 itineraries on the 12 routes, selecting from the list sets the timeline's pressed state and the map's selected-path layer (rendered features). On MCO-LAS, selecting from the timeline and by clicking a map path updates the other views and the detail panel |
| SC-003: links | Pass. All 144 itineraries on the 12 routes reopen from their addresses. Back and forward move between selections. An unknown route, or an itinerary not on its route, opens the default view with a note and a cleared address (FR-010). A component test counts history writes: one push per choice, none for repeating the current selection or for corrections, and one for a run of route-picker changes |
| SC-004: budgets | First-view scripts 90.8 KB gzip (budget 150). Map scripts 279.4 KB gzip (budget 300), loaded only when the map is shown. First-view data 22.3 KB gzip. Largest route file 12.9 KB gzip (LAX-DCA; budget 150). Lighthouse (`web-lighthouse`, CI, median of 3 mobile runs) passes: performance at least 0.90 and accessibility 1.00 |
| SC-005: accessibility and keyboard | Pass. axe finds no violations (WCAG 2.2 AA) at 360 and 1280 px, for the default view and for a route with a selected itinerary and the map shown. The scripted keyboard tests choose a route, select from the list (Enter) and the timeline (Space), and hear the live-region announcement. Every control, including the map canvas, gets the 3 px focus outline |
| SC-006: data additions reproduced | Pass. The pipeline suite passes: 548 tests (2 network tests deselected), and `schemas --check` is up to date. `verify` on c72cf16, again on 570cbca after the review round 1 fix to the hub times, and on 93ca8a3 after the round 2 definition change, reports: "identical: 23 outputs, the published showcase and the generated types match the committed files". All 144 itineraries satisfy the model's checks that the parts add up to the travel time and that the hub departure is the hub arrival plus the layover. The additions change no existing figure: the published itineraries, rates and comparisons are unchanged apart from the new fields and the build date |
| Visual references | 8 references: landing at 360 and 1280 px; error and loading at 360 px; a selected itinerary at 360 and 1280 px; a route with nothing selected at 1280 px; the map shown at 360 px. The map area is masked (plan, Complexity Tracking). Three consecutive runs in the pinned image passed, with 78 browser tests each |

## Notes

- **Map library:** MapLibre 5.24.1, not 6.18.0. Version 6's separate module worker never completed loading under Vite (research R1). Version 5 also keeps the map within its 300 KB budget.
- **Lighthouse locally:** on Windows with Playwright's Chromium, Lighthouse reported a single 10-second "unattributable" task (performance 70). Throttled browser traces here show no long task over 0.3 s, and CI's real Chrome on Linux passes. The local figure is a tooling artifact; CI is the reference.
- **Basemap in tests:** the fixture serves a local blank style (FR-016) and blocks every request outside the local server. One test serves the real style with its tiles blocked: the routes and the attribution still draw.
