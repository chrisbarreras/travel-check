---
description: "Task list for the web foundation"
---

# Tasks: Web Foundation

**Input**: Design documents from `specs/003-web-foundation/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: required.
- Display rules and data validation are written test-first: each test task is written, and seen to fail, before its implementation task (constitution, Principle II).
- Every component ships with its tests in the same change.

**Organization**: by user story (spec.md). All paths are from the repository root. Web code is under `web/`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: the user story (US1–US3) the task serves

---

## Phase 1: Setup

**Purpose**: the `web/` project, its toolchain and the validator generation.

- [ ] T001 Create web/package.json with exact pinned versions, each released at least two weeks before installation (research R5–R9); web/.nvmrc (Node 24) with `engines`; and web/package-lock.json from `npm install`. Add the scripts of contracts/checks.md (`gen`, `format:check`, `lint`, `typecheck`, `test`, `build`, `size`, `test:browser`, `test:browser:docker`, `test:visual:update`, `lighthouse`, `smoke`). Add `web/node_modules/`, `web/dist/`, `web/src/data/generated/`, `web/test-results/`, `web/playwright-report/` and `web/.lighthouseci/` to .gitignore, and `web/` to the .gitattributes LF rules
- [ ] T002 [P] Create web/tsconfig.json (strict, `noUncheckedIndexedAccess`) with the `@contract` path alias to shared/types/showcase.ts (research R9), plus web/vite.config.ts with the React plugin, the alias and the base path (`/travel-check/` when `GITHUB_PAGES=1`, `/` otherwise; research R4)
- [ ] T003 [P] Create web/eslint.config.js (typescript-eslint type-aware strict, react-hooks, jsx-a11y; warnings as errors), plus the `no-restricted-globals` and `no-restricted-imports` rules forbidding `fetch`, `XMLHttpRequest` and imports of `site-data` outside web/src/data/ (contracts/data-access.md, Enforcement). Also create web/.prettierrc.json for Prettier 3.10.1
- [ ] T004 [P] Write web/scripts/gen-validators.mjs. It compiles Ajv 2020-12 standalone validators for `ShowcaseIndex`, `RouteFile` and `ShowcaseManifest` from shared/schemas/showcase.schema.json into web/src/data/generated/validators.js with a `.d.ts` (research R3). It fails on a missing or invalid schema. Wire it as `npm run gen`, run before `typecheck`, `test` and `build`
- [ ] T005 [P] Create web/index.html with the title "Travel Check", `lang="en"`, the viewport meta and a `<noscript>` message linking to the repository and docs/methodology.md (spec, Edge Cases). Add a web/src/main.tsx stub, and web/src/styles/tokens.css with every color token of docs/design.md as CSS custom properties
- [ ] T006 Add the Vite build step that copies site-data/showcase/ unchanged into dist/data/showcase/, plus web/scripts/check-data-copy.mjs, which fails when any copied file's SHA-256 differs from its source (FR-016; research R4). Run the check as part of `npm run build`

**Checkpoint**: `npm ci && npm run gen && npm run typecheck && npm run build` succeed on an empty app.

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: the display rules and the data-access module that every story uses.

**⚠️ No user-story work starts before this phase is complete.**

### Tests first

- [ ] T007 [P] Write web/tests/unit/format.test.ts for web/src/format/:
  - **`percent`:** whole percent with halves rounded away from zero, at the boundaries (0.005, 0.995, 0.5, and the 1-of-128 tie cases of shared/test-cases/slack-feasibility.json).
  - **`points`:** signed whole points, negative halves.
  - **`interval`:** "95% interval +22 to +35 points".
  - **`similarOrBetter`:** decided on exact `ci_low`/`ci_high` per data-model.md `ShowcaseComparison.ci_low`/`ci_high`, including a rounded-zero case.
  - **`localTime`:** minutes to "12:38 pm", midnight, noon, and "+1 day" above 1,440 per data-model.md `Schedule.dep_local_min`/`arr_local_min`.
  - **`duration`:** "1 h 39 min".
  - **`period`:** "Jul 2024 – Jun 2025" per data-model.md `DataPeriod.start`/`end`.
  - **`rateText`:** `ok` against `insufficient_data` per data-model.md `Rate.status`, `Rate.rate` and `Rate.paired_days`.
  - **`excludedText`:** non-zero reasons only, per data-model.md `ShowcaseItinerary.excluded_days`.
  - **`flightNumbers`:** most frequent number, with "on N% of days" below 95%, per data-model.md `ShowcaseItinerary.find.legs[].flight_number`/`share_of_days`.
- [ ] T008 [P] Write web/tests/unit/airlines.test.ts. Every `airline` and `airline_out` in the committed site-data/showcase/ files has a display name, and an unknown code falls back to the code (data-model.md, Airline names).
- [ ] T009 [P] Write web/tests/unit/data-source.test.ts for `memorySource`, `staticSource` and `buildLandingView`:
  - Valid committed files load as `ok`.
  - A malformed file, a missing required field and an extra field each return `kind: "invalid"`, with no partial value (data-model.md `DataError.kind`; contracts/data-access.md, Guarantees 1–2).
  - A 404 returns `not_found` and a network error returns `network`.
  - `getRoute` rejects an id not in the index without fetching (Guarantee 3).
  - Each file is fetched once (Guarantee 4).
  - `buildLandingView` fails as `invalid` on each of the three cross-check cases (contracts/data-access.md, Cross-checks).
  - `staticSource` is tested with an injected `fetch` stub; there is no network.
- [ ] T010 [P] Write web/tests/unit/lint-rules.test.ts. It checks that the ESLint configuration forbids `fetch` outside web/src/data/, by linting two fixture files (contracts/data-access.md, Enforcement).

### Implementation

- [ ] T011 [P] Implement web/src/format/ (`percent`, `points`, `interval`, `similarOrBetter`, `localTime`, `duration`, `period`, `rateText`, `excludedText`, `flightNumbers`) until T007 passes (research R11)
- [ ] T012 [P] Implement web/src/format/airlines.ts until T008 passes
- [ ] T013 Implement web/src/data/ until T009 and T010 pass:
  - `types.ts`: `DataSource`, plus `Result` and `DataError` per data-model.md `Result<T>` and `DataError.kind`.
  - `validate.ts`, over the generated validators.
  - `staticSource.ts`, `memorySource.ts` and `buildLandingView.ts`.
  - `context.tsx`: `DataSourceContext` and `useLandingView()` with the loading, ready and error states of data-model.md, State.

**Checkpoint**: `npm test` passes; the display rules and the data access are complete and tested.

---

## Phase 3: User Story 1 — See a real example at a live link (Priority: P1) 🎯 MVP

**Goal**: the Travel Check page shows the landing comparison with every figure's sample, period and definition, at every size from 320 px up.

**Independent Test**: build from the committed data and open at phone and desktop sizes. Every figure equals the data files, with its sample, period and definition (spec, US1).

### Tests first

- [ ] T014 [P] [US1] Write web/tests/component/LandingComparison.test.tsx against `memorySource` with the committed files:
  - Route, airlines, hubs, flight numbers, local times, layover, "worked on X% of N days" and "not counted" appear as in data-model.md, Fields shown.
  - The difference, interval and days both flew appear as specified.
  - The "worked more often" statement is text, and the higher itinerary comes first (FR-005).
  - Definitions are verbatim from `index.definitions`.
  - The wording contains none of "chance", "will", "probability", "likely" (FR-004).
- [ ] T015 [P] [US1] Write web/tests/component/edge-cases.test.tsx with fixtures in web/tests/fixtures/:
  - an `insufficient_data` itinerary shows "insufficient data (N days)" and no percentage (FR-003);
  - an interval containing zero shows "similar" (FR-002);
  - a next-day arrival shows "+1 day";
  - different inbound and outbound airlines are both named.
- [ ] T016 [P] [US1] Write web/tests/component/Footer.test.tsx:
  - attributions verbatim from `index.attribution` with links;
  - the data period;
  - "Built 26 Nov 2026" from data-model.md `ShowcaseManifest.run.run_at`;
  - links to docs/methodology.md and the repository;
  - the copyright line "© 2026 Christopher T. Barreras Consulting" (FR-006, FR-007).
- [ ] T017 [US1] Write web/tests/e2e/landing.spec.ts. It reads site-data/showcase/ in the test, computes the expected texts with web/src/format/, and asserts them on the built page at 320, 360, 768 and 1280 px (FR-018, SC-003). It also asserts:
  - no horizontal scroll;
  - touch targets of at least 44 px;
  - reflow at 200% text zoom (SC-009);
  - the page title "Travel Check".

### Implementation

- [ ] T018 [P] [US1] Implement web/src/components/ItineraryCard.tsx: airline, hub, flight numbers, local times, layover, the rate text with its days, and not-counted days (data-model.md, Fields shown)
- [ ] T019 [P] [US1] Implement web/src/components/Difference.tsx: points, interval, days both flew, and the similar or more-often wording
- [ ] T020 [P] [US1] Implement web/src/components/Definition.tsx: a native `<details>` disclosure showing a definition's text verbatim, with a link to its methodology anchor in the repository and keyboard access (FR-004, FR-010)
- [ ] T021 [P] [US1] Implement web/src/components/Footer.tsx: attributions, period, build date, methodology and repository links, the copyright line and the font licence note
- [ ] T022 [US1] Implement web/src/components/LandingComparison.tsx and web/src/App.tsx (ready state): the "Travel Check" heading, the one-question lead, the "early version: one example" note (FR-007), the two cards in order and the difference. Wire the source in web/src/main.tsx with `staticSource(import.meta.env.BASE_URL)`. T014–T017 pass
- [ ] T023 [US1] Write web/src/styles/global.css per docs/design.md:
  - the fonts from `@fontsource-variable` (Latin, `font-display: swap`; research R8);
  - the 15 px base;
  - the 3 px accent focus outline;
  - 44 px targets;
  - the stacked phone layout and the side-by-side cards from 768 px;
  - the content capped at 1,360 px;
  - no motion under `prefers-reduced-motion` (FR-008, FR-009).

**Checkpoint**: US1 works locally. The page shows the real landing comparison and the e2e assertions pass.

---

## Phase 4: User Story 2 — Every change is checked automatically before it can merge (Priority: P1)

**Goal**: the full check suite runs in CI and blocks merges; `main` deploys to GitHub Pages with a smoke check.

**Independent Test**: one throwaway pull request per kind of breakage, each blocked; a clean pull request passes; a merge updates the live site (spec, US2; quickstart 11–14).

- [ ] T024 [US2] Write web/playwright.config.ts with the projects `e2e`, `visual`, `a11y`, `keyboard` and `smoke` (research R6):
  - `webServer` runs `vite preview` on dist/;
  - a shared fixture blocks every request outside the local server (FR-022);
  - the `visual` project refuses to run unless `PLAYWRIGHT_DOCKER=1`;
  - animations are disabled;
  - `smoke` is excluded from `test:browser`.
- [ ] T025 [P] [US2] Add web/docker/playwright.Dockerfile, based on `mcr.microsoft.com/playwright:v1.65.0-noble` pinned by digest, plus the `test:browser:docker` and `test:visual:update` scripts that mount the repository and run the matching projects in it (FR-019, FR-026)
- [ ] T026 [P] [US2] Write web/tests/visual/landing.spec.ts: screenshots of the ready state at 360 and 1280 px, and of the loading and error states at 360 px. Generate the reference images in web/tests/visual/__screenshots__/ with `npm run test:visual:update`
- [ ] T027 [P] [US2] Write web/tests/a11y/axe.spec.ts: `@axe-core/playwright` with the `wcag2a`, `wcag2aa`, `wcag21aa` and `wcag22aa` tags, at 360 and 1280 px, for the ready and error states, with zero violations allowed (FR-020, SC-004)
- [ ] T028 [P] [US2] Write web/tests/keyboard/keyboard.spec.ts. It is a scripted Tab and Shift+Tab walk over every link and disclosure, asserting:
  - the expected order;
  - a visible focus outline, as the computed 3 px outline;
  - Enter and Space open the definitions (FR-010, SC-004).
- [ ] T029 [P] [US2] Write web/lighthouserc.json (3 runs, mobile preset, `staticDistDir` dist/; assertions performance ≥ 0.90, accessibility = 1.00, LCP ≤ 2,500 ms, CLS ≤ 0.1; reports kept locally) and web/.size-limit.json (all of dist/assets/*.js at most 150 KB gzip) (research R7, SC-001, SC-002)
- [ ] T030 [P] [US2] Write web/scripts/check-data-size.mjs. It fails when the files the first view loads (index, landing and manifest) are above 150 KB gzip, and prints each file's size. Include it in `npm run size` (SC-002)
- [ ] T031 [US2] Write web/tests/smoke/live.spec.ts, run by `npm run smoke -- <url>`. It loads the deployed URL and asserts the landing figures against dist/data/showcase/. It is the only network-using test, outside `test:browser` (FR-025)
- [ ] T032 [US2] Write .github/workflows/web.yml per contracts/checks.md and research R12:
  - jobs `web-checks`, `web-browser` (the pinned container) and `web-lighthouse` on every push and pull request, with no path filters;
  - failure artifacts: the Playwright report, the diffs and the Lighthouse reports;
  - `web-deploy` on push to `main` only, needing all three: build with `GITHUB_PAGES=1`, `actions/upload-pages-artifact`, `actions/deploy-pages` with `pages: write` and `id-token: write`, then `npm run smoke` against the deployed URL.
- [ ] T033 [US2] Write docs/adr/0015-static-hosting-github-pages.md (research R1, R2), mark ADR-0002's frontend-hosting row as superseded by ADR-0015, and add it to docs/adr/README.md
- [ ] T034 [US2] With the owner's authorization, enable GitHub Pages with "GitHub Actions" as the source on `chrisbarreras/travel-check`. Create the ruleset on `main`: pull request required; the status checks `checks` (pipeline), `web-checks`, `web-browser` and `web-lighthouse` required; force pushes and deletion blocked (research R2, R13; FR-024). Record the `gh api` commands in docs/architecture.md
- [ ] T035 [US2] Run the breakage tests of quickstart 11: one throwaway pull request per breakage (lint, type, unit, component, e2e, visual, a11y, keyboard, budget), each closed unmerged, plus a clean one. Record each pull request, its failing check and its blocked merge state in specs/003-web-foundation/validation.md (SC-005)

**Checkpoint**: the checks block bad merges, and `main` is live at https://chrisbarreras.github.io/travel-check/.

---

## Phase 5: User Story 3 — Data loading in one place, with honest failures (Priority: P2)

**Goal**: the loading and error states are honest, and the data source is swappable without changing screens.

**Independent Test**: the page against the committed, a malformed and a failing source shows, respectively, the example, the plain error and the plain error, with no screen-code changes (spec, US3).

- [ ] T036 [P] [US3] Write web/tests/component/states.test.tsx:
  - the loading state shows the layout's shape and no digits;
  - a malformed landing file, a missing comparison and a network failure each show "This example could not be loaded", with no figures;
  - the same `App` renders all three with only the source swapped (FR-013, FR-014; data-model.md, State).
- [ ] T037 [P] [US3] Add an e2e case to web/tests/e2e/states.spec.ts. Route interception serves a malformed landing.json, then delays the response, and the test asserts the error and loading states in the real browser.
- [ ] T038 [US3] Implement web/src/components/Skeleton.tsx and web/src/components/LoadError.tsx, and wire the loading and error states in web/src/App.tsx, until T036 and T037 pass. The visual references from T026 for these states are updated deliberately.

**Checkpoint**: all three stories work independently.

---

## Phase 6: Polish and cross-cutting

- [ ] T039 [P] Write docs/architecture.md: the one-page system overview. It covers the data flow from the pipeline, through site-data/showcase/ and the copy into dist/, then the `DataSource` and validators, to the page. It also lists the CI jobs and the deployment, and where Phase 2's API plugs in (FR-027)
- [ ] T040 [P] Update README.md for Travel Check: status, live link, how to run, test and build web/ (the commands of contracts/checks.md), and the Docker requirement for browser tests (FR-027)
- [ ] T041 [P] Mark `web-foundation` done in the docs/roadmap.md Phase 1 table once deployed, linking to specs/003-web-foundation/
- [ ] T042 Run every quickstart scenario and record the results in specs/003-web-foundation/validation.md:
  - the budgets measured: JS and data gzip, the Lighthouse medians;
  - the CI job times (SC-007);
  - three reruns of `web-browser` on one commit (SC-006);
  - the deploy-to-live time (SC-008).
- [ ] T043 Run the independent review: a new `feature-reviewer` agent, given only `specs/003-web-foundation` and the base branch `main`. Save its report as specs/003-web-foundation/review.md. Fix the BLOCKING findings and answer the SHOULD-FIX findings in review.md. Repeat with a new reviewer until the verdict is APPROVE (constitution, Development Workflow)

---

## Dependencies

- Setup (T001–T006) → Foundational (T007–T013) → user stories.
- **US1** (T014–T023) needs Foundational.
- **US2** needs the US1 page so the browser tests have something to test:
  - T024–T031 can start once T022 exists;
  - T032 needs T024–T031;
  - T034 needs T032 on `main`, so it runs after this feature's pull request is open. The ruleset can be created before merge, and Pages enabled before the first deployment;
  - T035 needs T034.
- **US3** (T036–T038) needs Foundational. It can run in parallel with US1, but shares web/src/App.tsx with T022, so T038 comes after T022.
- Polish needs all stories. T043 is last.

## Parallel examples

- **Foundational tests:** T007, T008, T009 and T010 together, then T011 and T012 together.
- **US1 tests and components:** T014, T015 and T016 together, then T018, T019, T020 and T021 together.
- **US2 checks:** T025, T026, T027, T028, T029 and T030 together, after T024.

## Implementation strategy

- **MVP = US1:** the real example on a page, verified locally by e2e.
- **US2 then makes it live and guarded.** It is the same priority, but depends on the page.
- **US3 hardens the failure paths.**
- Commit per user story. Push when CI should run.
