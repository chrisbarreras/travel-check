# Feature Specification: Web Foundation

**Feature Branch**: `003-web-foundation`

**Created**: 2026-11-27

**Status**: Draft

**Input**: User description: "Phase 1 feature web-foundation from docs/roadmap.md (feature short name: web-foundation). The frontend foundation for the Phase 1 static showcase explorer: a Vite + React + TypeScript app in web/ that reads the committed showcase JSON (site-data/showcase/, typed by the generated shared/types/showcase.ts from feature 002), with the full automated test setup: unit and component tests, Playwright end-to-end tests, visual regression tests run in Docker so screenshots are reproducible, axe accessibility checks, and Lighthouse CI with performance and accessibility budgets. CI (GitHub Actions) runs lint, type checks, all tests and the build, and blocks merges to main on failure. It deploys a placeholder page as a static site, which shows real figures from the showcase data (for example the landing example's two itineraries and their connection shares with sample size and data period, per constitution Principle I) and follows docs/design.md (palette, typography, accessibility; risk never shown by color alone). Data access goes through one small module (for example getIndex() and getRoute(id)) so later features, and Phase 2's API, can change the data source in one place. Works on phones. Out of scope: the map, list and timeline (explorer-core), risk visuals, transfer-time slider and insight panels (explorer-insights), the API and search (Phase 2)."

## Context

Phase 1 ships a static showcase explorer (roadmap, Phase 1; ADR-0001). Feature 002 produced the data: validated showcase files for 12 routes, an index and a landing file holding one striking comparison, with generated types. This feature builds the web application those files feed, with the checks every later Phase 1 feature relies on. It ends with a live page at a public address. The page is a placeholder, but it shows real numbers from the data. The map, list, timeline and insight panels come in `explorer-core` and `explorer-insights`.

## Clarifications

### Session 2026-11-27

The owner asked for recommendations to be adopted directly, so each answer below is the recommended option.

- Q: Which day count is N in "worked on X% of N days"? → A: The days the itinerary operated in the period and could be judged: the result's paired days, which is the rate's own denominator. Days at the end of the period, and days excluded for data reasons, are not in N. Each such category is counted on the page as "not counted".
- Q: Should pull requests get their own preview deployment, and do the performance checks run against the live site? → A: No preview deployments are required. The performance and accessibility checks run in CI against the production build served locally, so they need no network and give stable results. The deployed site gets an automated smoke check after each deployment.
- Q: In which time zone are scheduled times shown? → A: Each time is shown in the local time of its own airport and labelled as local, as in the showcase data. All stored times stay in UTC or schedule-local minutes from the pipeline. The page does no time-zone arithmetic of its own (constitution, Principle IV).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See a real example at a live link (Priority: P1)

A reviewer, for example a hiring manager opening the link from a CV on their phone, opens the site's public address. Within a few seconds they see the project's one question: how often did this connection work, and is there a better one? A real example answers it: the landing comparison from the showcase data. That is two one-stop itineraries on the same route through different hubs. Each shows its flights, hub and airline, and the share of days the connection worked, with the number of days and the data period. The difference between the two is shown with its 95% interval, and a plain sentence says what the numbers mean. Every number comes from the committed data. Nothing is typed in by hand.

**Why this priority**: the deployed page is the Phase 1 promise in its smallest form. It proves the data, the build and the hosting work end to end, and it gives the project a link to share from the first feature on.

**Independent Test**: build the site from the committed showcase data and open it in a phone-sized and a desktop-sized browser. The landing comparison's figures must match the data files exactly, each with its sample size, period and definition. The same check runs against the deployed address after each deployment.

**Acceptance Scenarios**:

1. **Given** the committed showcase data, **When** a visitor opens the site, **Then** they see the landing route, both itineraries (flight numbers, airline, hub, scheduled times) and, for each, "worked on X% of N days, Jul 2024 – Jun 2025". X and N must be exactly the values in the landing file.
2. **Given** the landing comparison, **When** the page shows the difference between the two itineraries, **Then** it is in whole points, with its 95% interval and the number of days both itineraries operated. The wording is historical ("worked on"), never predictive ("chance", "will make it").
3. **Given** a phone-sized screen (360 px wide), **When** the page loads, **Then** everything is readable without horizontal scrolling, and touch targets are at least 44 px.
4. **Given** any figure on the page, **When** a visitor looks for its meaning, **Then** a definition is on the page or one step away, together with its sample size and data period (constitution, Principle I).
5. **Given** the page, **When** it states which itinerary worked more often, **Then** that is shown by text and position as well as color (constitution, Principle V).
6. **Given** the page footer, **When** a visitor reads it, **Then** it credits the data sources (BTS on-time, DB1B and T-100 data, and airportsdata). It also states the data period and links to the methodology and the source repository.

---

### User Story 2 - Every change is checked automatically before it can merge (Priority: P1)

The project owner, or a later feature's implementer, opens a pull request. Automated checks run without anyone starting them: lint, type checks, unit and component tests, end-to-end browser tests, visual comparison against reviewed reference images, accessibility checks including keyboard use, and performance and size budgets. A failure in any of them blocks the merge. The page then deploys automatically from `main`.

**Why this priority**: the constitution makes automated verification non-negotiable (Principle II) and forbids manual testing in any definition of done. Every later Phase 1 feature adds screens on top of these checks. Without them, the explorer features would each have to build them. The checks also catch regressions in work already done.

**Independent Test**: open a pull request that deliberately breaks each kind of check in turn: a lint error, a type error, a failing unit test, a changed screenshot, an accessibility violation, a removed keyboard path, and a bundle over budget. Each must fail and block the merge. A clean pull request must pass. A merge to `main` must update the live page.

**Acceptance Scenarios**:

1. **Given** a pull request to `main`, **When** any check fails, **Then** the merge is blocked, and the failing check names what failed.
2. **Given** an intended visual change, **When** the reference images are updated, **Then** that happens only through a deliberate, reviewable update that shows the old and new images. No check updates them on its own (constitution, Principle II).
3. **Given** the same commit, **When** the visual comparison runs on a developer machine and in CI, **Then** the results are the same, because both run in the same pinned container environment.
4. **Given** the test suite, **When** it runs, **Then** it uses no network access and is deterministic across runs.
5. **Given** a merge to `main` with all checks green, **When** deployment runs, **Then** the live page serves the new build. A failed deployment leaves the previous version live.
6. **Given** a change to the data contract that makes the generated types stale, **When** checks run, **Then** they fail. That check already exists from feature 002; the web build must use the generated types, not hand-written copies (constitution, Principle IV).

---

### User Story 3 - Data loading in one place, with honest failures (Priority: P2)

The developer of the next features, and later the Phase 2 API, needs to change where showcase data comes from without touching screens. Every screen asks one data-access module for the index, the landing comparison or a route. That module checks what it receives against the data contract. When data is missing, malformed or fails to load, the visitor sees a plain message saying the example could not be loaded. They never see a broken layout, a blank page or a made-up number.

**Why this priority**: it is cheap now and expensive later. The roadmap's Phase 2 decision (static files, API or both) depends on the data source being replaceable in one place. It matters less to a first-time visitor than Stories 1 and 2, hence P2.

**Independent Test**: run the page against three substituted data sources: the committed files, a source returning a malformed landing file, and a source that fails to respond. The first shows the example. The other two show the plain error message with no figures. No screen code changes between the three.

**Acceptance Scenarios**:

1. **Given** the committed data, **When** a screen needs the index, the landing comparison or a route, **Then** it gets it only through the data-access module. No screen fetches files directly.
2. **Given** a data file that does not match the data contract, **When** it loads, **Then** the module rejects it, the page shows "This example could not be loaded", and no partial figures appear.
3. **Given** a slow connection, **When** the data is loading, **Then** the page shows the layout's shape, not a spinner over empty space, and no placeholder numbers (design.md, Interaction and motion).
4. **Given** a test, **When** it needs data, **Then** it can substitute a fixed in-memory source through the same module.

### Edge Cases

- The landing file names an itinerary that is missing from its own itinerary list: treated as malformed data (Story 3), never shown half-filled.
- An itinerary's result is below the minimum sample: the page shows "insufficient data" instead of a rate, never a percentage. This cannot happen with today's landing example, but the display rule is tested with fixture data.
- The difference's interval crosses zero: the page says the two worked on a similar share of days, not that one is better. This is tested with fixture data.
- Very long airport or airline names on a 320 px screen: they wrap without overlapping or overflowing the page.
- Text enlarged to 200% in the browser: the content reflows and stays usable.
- The visitor prefers reduced motion: no transitions.
- JavaScript disabled or failing: the page shows a short message that the example needs JavaScript, with links to the repository and methodology. That is acceptable for a placeholder.
- Fonts fail to load: system fonts are used, with no invisible text while waiting.
- The committed data changes: the page shows the new figures after the next build with no code change. Visual reference images that contain numbers are updated deliberately in the same change.

## Requirements *(mandatory)*

### Functional Requirements

**Placeholder page**

- **FR-001**: The site MUST show the landing comparison from the committed showcase data:
  - the route, as origin and destination airport codes. The showcase data has no city names, and adding them is out of scope;
  - both itineraries, each with its airline, hub, flight numbers, scheduled local departure and arrival times, and scheduled layover;
  - for each itinerary, the share of days it worked as a whole percent, with the number of days counted (the result's paired days) and the data period. Days not counted are given as a number with their reason;
  - scheduled times in each airport's local time, labelled as local.
- **FR-002**: The site MUST show the difference between the two itineraries in whole points. It MUST also show the 95% interval and the number of days both operated. When the interval includes zero, the wording MUST say the two are similar rather than that one is better.
- **FR-003**: Below the minimum sample, the site MUST show "insufficient data" instead of a rate (constitution, Principle I). Precision MUST follow the methodology's precision rules: whole percent for rates and whole points for differences.
- **FR-004**: Every figure MUST have a plain-language definition available on the page, taken from the definitions published in the showcase index, not written separately in the site. It MUST also state its sample size and data period. Wording MUST be historical, never predictive (design.md, Wording).
- **FR-005**: Which itinerary worked more often MUST be shown by text and position, not by color alone (constitution, Principle V).
- **FR-006**: The page MUST have a footer with:
  - the data-source attributions published in the showcase index (BTS on-time performance, DB1B and T-100 data, and the airport data source);
  - the data period and the date the data was built, from the showcase manifest;
  - links to the methodology document and the source repository.
- **FR-007**: The page MUST say plainly that this is an early version: one example, with the full explorer to follow. It MUST NOT show controls that do nothing.
- **FR-008**: The page MUST follow `docs/design.md`: the color tokens and their contrast, the typography, the 44 px touch targets, the visible 3 px focus outline, the stacked phone layout, and no motion under `prefers-reduced-motion`.
- **FR-009**: The page MUST work from 320 px wide up to desktop with no horizontal scrolling. It MUST also reflow at 200% text zoom.
- **FR-010**: Every interactive element (links, and any disclosure that shows definitions) MUST work by keyboard, in a sensible order, with visible focus and screen-reader labels.

**Data access**

- **FR-011**: All showcase data MUST be loaded through one data-access module. It provides at least the index, the landing comparison and a route by its identifier. Screens and components MUST NOT load data any other way.
- **FR-012**: The data-access module MUST check loaded data against the generated data contract before handing it to screens. Data that fails the check MUST be rejected as a whole.
- **FR-013**: The data source behind the module MUST be replaceable without changing screens: the committed static files in production, and a fixed in-memory source in tests. A future API must be able to take its place.
- **FR-014**: When data is loading, the page MUST show the layout's shape without numbers. When loading fails or the data is rejected, it MUST show a plain error message with no figures.
- **FR-015**: The site's data types MUST come only from the generated types of feature 002, never from hand-written copies (constitution, Principle IV).
- **FR-016**: The site MUST serve the committed showcase files unchanged. The build MUST NOT recompute or edit any figure.

**Automated checks**

- **FR-017**: The project MUST have automated:
  - lint and formatting checks;
  - type checks;
  - unit tests for pure logic (formatting of rates, differences, dates and times; display rules such as "insufficient data" and "similar");
  - component tests;
  - end-to-end tests in a real browser at phone and desktop sizes.
- **FR-018**: End-to-end tests MUST assert that the figures on the page equal the values in the data files they were built from.
- **FR-019**: Visual regression tests MUST compare screenshots of the page at phone and desktop sizes against committed reference images. They MUST run in a pinned container environment, so results do not depend on the machine. Reference images MUST change only through a deliberate update that can be reviewed.
- **FR-020**: Accessibility checks MUST run automated rule checks (no violations at WCAG 2.2 AA level) and scripted keyboard tests covering every interactive element.
- **FR-021**: Performance checks MUST enforce the budgets in the Success Criteria (load time, script size, data size), and fail when a budget is exceeded.
- **FR-022**: All tests MUST be deterministic and MUST NOT use the network. Tests that need data use the committed files or in-memory fixtures.
- **FR-023**: Continuous integration MUST run every check above, together with the existing pipeline checks, on every pull request and on every push to `main`.
- **FR-024**: Merges to `main` MUST be blocked unless all required checks pass.
- **FR-025**: The site MUST deploy automatically from `main` once checks pass. A failed deployment MUST leave the previous version live. After each deployment, an automated smoke check MUST confirm that the live page loads and shows the landing figures. This is the only check that uses the network, and it runs outside the test suite. Performance and accessibility checks run in CI against the production build served locally; preview deployments for pull requests are not required.
- **FR-026**: Developers MUST be able to run every check locally with documented commands. That includes the visual tests in the same container environment as CI.

**Documentation**

- **FR-027**: The README MUST link to the live site and explain how to run, test and build the web application. `docs/architecture.md` MUST describe the data flow from the pipeline's showcase files through the data-access module to the page.

### Key Entities

- **Showcase index**: the list of curated routes and the identifier of the landing comparison, with the curation balance. Produced by feature 002.
- **Landing data**: the landing route, its comparisons (the landing comparison is marked) and both itineraries' full data, plus disruption notes and the data period. Produced by feature 002.
- **Showcase manifest**: provenance of the published data, including the build time and source checksums. Used for the footer's data date.
- **Data source**: what the data-access module reads from. That is the static files in production, an in-memory fixture in tests, and possibly the Phase 2 API later.
- **Reference image**: a reviewed screenshot of the page at one screen size, used by the visual regression tests.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A visitor on a mid-range phone with a throttled mobile connection, using the standard lab profile of the performance check, sees the landing comparison's figures within 2.5 seconds. The page's performance score is at least 90 and its accessibility score is 100.
- **SC-002**: The page's scripts total at most 150 KB compressed, and the data the page loads at most 150 KB compressed. Today's index and landing files are 7.0 KB.
- **SC-003**: 100% of the figures on the page match the committed data files. This is checked automatically on every pull request.
- **SC-004**: Automated accessibility checks report zero violations at WCAG 2.2 AA level at phone and desktop sizes. Every interactive element is reached and used by keyboard in the scripted tests.
- **SC-005**: Each kind of deliberate breakage blocks the merge in a test pull request: lint, type, unit, component, end-to-end, visual, accessibility, keyboard and budget. A clean pull request passes.
- **SC-006**: Visual tests give the same result on a developer machine and in CI for the same commit. Three consecutive CI runs of an unchanged commit all pass.
- **SC-007**: The full web check suite completes in CI in under 15 minutes.
- **SC-008**: A merge to `main` is live at the public address within 10 minutes of the checks passing.
- **SC-009**: The page reads correctly from 320 px to 1920 px wide and at 200% text zoom, verified by the visual and end-to-end tests at 320, 360, 768 and 1280 px.

## Out of Scope

- The map, itinerary list and timeline, synced selection, and selection kept in the URL (`explorer-core`).
- Risk visuals (reliability meter, failure bar, month chart), the transfer-time slider, the traveler-insight panels, "Find this itinerary" links, and the "How the numbers work" page (`explorer-insights`).
- Routes other than the landing route on the page. The data-access module can load them, but no screen shows them yet.
- Any API, server-side code, search, or paste parsing (Phase 2).
- Changes to the pipeline or the data contract, beyond what the web build needs to read the existing generated types.
- Analytics, cookies, accounts and a custom domain.

## Assumptions

- **Tools:** follow ADR-0002 and the constitution: React, TypeScript and Vite; Vitest and Testing Library; Playwright for end-to-end and visual tests; axe-core; Lighthouse CI; GitHub Actions.
- **Hosting:** a free static host from ADR-0002, Cloudflare Pages or Vercel. The choice is confirmed against current free-tier terms during planning. Connecting the host and turning on branch protection for `main` need the repository owner's accounts. Those one-time steps are documented, and the owner may be asked to authorize them.
- **Showcase files:** the committed files in `site-data/showcase/` are the input. The build copies them in, so the site always shows the data at the same commit.
- **Fonts:** self-hosted rather than loaded from Google Fonts, so tests need no network and the page makes no third-party requests. Both fonts are under the SIL Open Font License.
- **Budgets:** the performance budgets are this phase's budget under constitution Principle V and ADR-0009. Later Phase 1 features may revise them in their own specs, for example when the map arrives.
- **Methodology link:** "methodology" links to `docs/methodology.md` in the repository until `explorer-insights` adds the in-app "How the numbers work" page.
