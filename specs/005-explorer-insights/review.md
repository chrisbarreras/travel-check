# Independent review: Explorer Insights

Each round is a new `feature-reviewer` agent, given only `specs/005-explorer-insights` and, while feature 004 awaits merge, the base branch `004-explorer-core` (constitution, Development Workflow).

## Round 1 (004-explorer-core...35b4b60)

**Verdict:** CHANGES REQUIRED. 2 blocking, 3 should-fix, 5 nits.

**Automated checks, all passing:** format, lint and typecheck; 384 tests; build; size (95.1 KB first view); 110 browser tests in the pinned image; `schemas --check`; the pipeline's slack tests.

### Findings and responses

| # | Severity | Finding | Response |
|---|---|---|---|
| 1 | BLOCKING | 10 of 59 faster alternatives point to itineraries not published on the route. Their raw-id button sent the visitor to the default example. | **Fixed.** An alternative is a button only when it is on the route. Otherwise it is named from its id ("United via DEN (not shown on this route)") with its full evidence, and isn't selectable. A test clicks every selectable alternative on every itinerary and checks it is selected on the same route. The per-itinerary test checks that the others are text. |
| 2 | BLOCKING | Panel content and keyboard use were largely untested, while validation.md claimed SC-003 and SC-004. | **Fixed.** The per-itinerary component test now checks every panel against the data. That covers alternatives (content and difference direction), better and other options, the buffer sentence, failure counts with sample and the dominant sentence, monthly values, markers and notes (dates, text, source), all 866 schedule changes, sold passengers and the find link. The keyboard project covers the method view (Tab and Enter from the header, and back), the slider, and choosing an alternative with Enter. A synthetic test covers insufficient data in the slider (US1 AS4) and a 45-minute default. validation.md is rewritten to what the tests check. |
| 3 | SHOULD-FIX | The failure, monthly and buffer panels don't follow the slider and didn't say their setting or sample. | **Fixed.** Each says it is "at the published 30-minute minimum connection time" with its days and period. The failure panel adds that the slider doesn't change its counts. |
| 4 | SHOULD-FIX | The faster alternative's interval didn't say its direction. | **Fixed.** "The faster one minus this one: 95% interval −1 to +6 points", asserted for every alternative. |
| 5 | SHOULD-FIX | Definitions didn't link to the method view, as the clarification said. | **Spec amended.** The method view is linked from the header. Each definition keeps its link to its own methodology section: a second link in each of the page's many definitions would double their tab stops. |
| 6 | NIT | A rate shown as 95% could fill 9 or 10 dots. | **Fixed.** The meter fills from the whole percent shown, so dots and text always agree. |
| 7 | NIT | Small-sample months show "12 d", and the legend said "flown". | **Spec amended** to the abbreviation, which fits 12 narrow columns. Screen readers hear "12 days, too few for a rate". The legend now says "the days counted". |
| 8 | NIT | The `disruption_note` definition wasn't shown with the notes. | **Fixed.** It is under the monthly view and required by the route view's checks. |
| 9 | NIT | architecture.md contradicted itself. | **Fixed.** The old sentence is removed. |
| 10 | NIT | Insufficient data and a non-default minimum weren't tested in the UI. | **Fixed** by the synthetic test in finding 2. |
