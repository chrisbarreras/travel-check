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

## Round 2 (004-explorer-core...ecdb901)

**Verdict:** CHANGES REQUIRED. 1 blocking, 3 should-fix, 5 nits.

**Automated checks, all passing:** format, lint and typecheck; 387 tests; build; size (95.3 KB first view); 112 browser tests in the pinned image; `schemas --check`; the pipeline's slack and slider tests.

The reviewer confirmed every round 1 fix.

### Findings and responses

| # | Severity | Finding | Response |
|---|---|---|---|
| 1 | BLOCKING | Monthly rates showed no visible sample size (Principle I); the days were only in screen-reader text. | **Fixed.** Every month with a rate shows its days under its percentage ("31 d"), with a legend. The per-itinerary test asserts each month's visible days. |
| 2 | SHOULD-FIX | The other connecting options showed no interval (US3 AS2). | **Fixed.** Each shows "95% interval … against this one" where it is published. This is asserted on every itinerary. |
| 3 | SHOULD-FIX | The selected card's published rate sat above the slider's recomputed one without naming its setting. | **Fixed.** A note under the card says its rate is "at the published 30-minute minimum connection time and 15-minute boarding cutoff", and points to the slider. This is asserted on every itinerary. |
| 4 | SHOULD-FIX | The buffer and connection share had no minimum-sample rule, and the buffer's null case said something false. | **Fixed.** Below the minimum sample both say "Insufficient data (N days, period)", with no percentage. The null case (no operated days) says exactly that. A synthetic test covers both. |
| 5 | NIT | T008 was unticked. | **Fixed.** T008 ticked; T009 is ticked at approval. |
| 6 | NIT | Lighthouse audited only the landing view. | **Fixed.** `lighthouserc.json` also audits a selected itinerary with its slider and panels. Locally both score 100 for accessibility, with LCP under 1.5 s and CLS 0. |
| 7 | NIT | The method view showed keys reworded. | **Fixed.** Each definition shows its readable name and its raw key (`connection_feasibility`). |
| 8 | NIT | The focus-outline walk skipped the new controls. | **Fixed.** A keyboard test tabs through every control on a selected itinerary, with all definitions open (over 40 stops), and requires the 3 px outline on each. |
| 9 | NIT | Two counts said "in the period" without naming it. | **Fixed.** Both name the period. |
