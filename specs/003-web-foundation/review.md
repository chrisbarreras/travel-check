# Independent review: Web Foundation

Each round is a new `feature-reviewer` agent, given only `specs/003-web-foundation` and the base branch `main` (constitution, Development Workflow).

## Round 1 (main...9e6ec67)

**Verdict:** CHANGES REQUIRED. 1 blocking, 5 should-fix, 5 nits.

**Automated checks, all passing:** `gen`, `format:check`, `lint`, `typecheck`, 95 unit and component tests, `build` (15 files byte-identical), `size` (JS 84.95 KB gzip, data 8.8 KB), and 21 browser tests in the pinned image. Lighthouse could not run on the reviewer's machine; it passed in CI.

**The reviewer also verified:**
- breakage pull requests #2–#10 against their logs;
- the three identical `web-browser` reruns;
- the ruleset (four required checks, no bypass actors) and the Pages setting.

### Findings and responses

| # | Severity | Finding | Response |
|---|---|---|---|
| 1 | BLOCKING | Flight-number shares were shown as percentages ("DL3080 (on 35% of days)") with no definition, sample or period (Principle I). | **Fixed.** The share is no longer shown. Cards read "Most often DL3080, then DL524; flown under other numbers on some days" when a leg used other numbers on more than 5% of days. The e2e test asserts that the only percentages on the page are the two rates, apart from the labelled "95% interval". |
| 2 | SHOULD-FIX | Data that passes the contract could still blank the page: no error boundary, `run_at` checked only by prefix, and `count_feasible > paired_days` allowed. | **Fixed.** `ErrorBoundary` wraps the app and renders the plain message. `buildLandingView` parses `run_at` as it will be displayed: impossible dates such as 2026-13-45 and 31 Feb are rejected. It also rejects more feasible days than paired days. Component and unit tests cover each case, including a throw during rendering. |
| 3 | SHOULD-FIX | An insufficient-data itinerary was still ranked and compared. | **Fixed.** When either itinerary is below the minimum sample, the page shows no verdict, badge, difference or difference definition. It says "One of these itineraries has too few days for a rate, so the two are not compared." The edge-case test asserts that each of those is absent. |
| 4 | SHOULD-FIX | The e2e "figures equal the data" check used the formatting code under test to build its expected values, and covered only some figures. | **Fixed.** The expected texts are hand-checked literals in `tests/fixtures/landing-expected.ts`. A test ties them to the raw data values, so a data change fails until the texts are rechecked. The e2e test now covers every figure: heading, summary, both cards (flights, times, layover, travel time, rate, not-counted days), the difference, the footer's period, build date and attributions. The smoke check uses the same literals. |
| 5 | SHOULD-FIX | `web-browser` built with the image's Node 26, not Node 24. | **Fixed in CI.** The job installs Node 24 with `actions/setup-node` before building, like the other jobs. For local Docker runs, `engines` now reads `>=24`, so the image's Node 26 doesn't warn. Local Docker runs exist to compare screenshots; CI builds everything that is tested and deployed with Node 24. |
| 6 | SHOULD-FIX | The spec's edge cases had no tests: JavaScript disabled, very long names, JavaScript failing. | **Fixed.** `tests/e2e/edge.spec.ts` checks the noscript message and its two links with JavaScript disabled. It also checks 60-character flight numbers at 320 px with no horizontal scroll. JavaScript failing at render is covered by the error-boundary test (finding 2). |
| 7 | NIT | The `/travel-check/` build was never tested before going live. | **Fixed.** `web-deploy` runs the e2e project against the Pages build, served at `/travel-check/`, before deploying. Playwright passes the base path to `vite preview`. Without it, the preview's fallback silently served the page for data URLs, which the new local run exposed. |
| 8 | NIT | Outside Docker, the visual project was skipped silently. | **Fixed.** Playwright prints a warning outside the container, and contracts/checks.md now says the project is skipped with a warning, not refused. |
| 9 | NIT | The rate line didn't carry the period, unlike acceptance scenario 1. | **Fixed.** "worked on 92% of 298 days, Jul 2024 – Jun 2025". |
| 10 | NIT | Below 95%, the threshold and the rounded share could contradict each other. | **Resolved by finding 1:** no share is shown. |
| 11 | NIT | The README called the site live before its first deployment; the roadmap cited "#1" for feature 002, which is this feature's number in the public repository. | **Fixed.** The README says the site deploys from `main` once this feature merges. The roadmap gives the merge date instead of a PR number. |

**After the fixes:** 100 unit and component tests pass. 24 browser tests pass in the pinned image, with the visual references regenerated for the new flight and rate wording and reviewed. 15 e2e tests pass against the `/travel-check/` build. JS is 85.4 KB gzip.

## Round 2 (main...7875d1a)

**Verdict:** CHANGES REQUIRED. 1 blocking, 2 should-fix, 4 nits.

**Automated checks, all passing:** `gen`, `format:check`, `lint`, `typecheck`, 100 unit and component tests, `build`, `size` (JS 85.39 KB gzip), and 24 browser tests in the pinned image. CI `web-lighthouse` passed. The reviewer confirmed the ruleset (active, no bypass actors, four required checks).

### Findings and responses

| # | Severity | Finding | Response |
|---|---|---|---|
| 1 | BLOCKING | ADR-0002's "shadcn/ui + Tailwind CSS" and "TanStack Query" rows were dropped without a superseding ADR, and the plan's Constitution Check claimed a pass. | **Fixed.** [ADR-0016](../../docs/adr/0016-plain-css-and-own-data-hook.md) records plain CSS with design tokens and native controls, and the data-access module instead of a data-fetching library. It states when to revisit each: composite widgets for styling, Phase 2's API for fetching. It supersedes both ADR-0002 rows, which are marked. The ADR index, the plan's Constitution Check row and research (R10, new R14) are updated. |
| 2 | SHOULD-FIX | A definition the page shows could be missing from a contract-valid index, and the figure would appear without it. | **Fixed.** `buildLandingView` rejects an index that lacks any of the six definitions the page can show. There is one unit test per key. |
| 3 | SHOULD-FIX | The keyboard test never reached the links inside the definitions. | **Fixed.** The test first opens every definition with Enter. It then walks all 15 controls, including the 5 "How this is computed" links, and checks order, Shift+Tab and the 3 px outline on each. |
| 4 | NIT | The page shows the rate from its counts, and `Rate.rate` was never checked against them. | **Fixed.** A rate with status `ok` must equal its counts, rounded as the pipeline stores it. Otherwise the data is rejected (unit test). |
| 5 | NIT | The rule that `itinerary_a` has the higher rate was assumed, not checked. | **Fixed.** A comparison with `difference < 0` or `ci_low > ci_high` is rejected (unit test). |
| 6 | NIT | "Insufficient data" gave no threshold and no definition. | **Fixed.** When an itinerary is below the minimum sample, the summary says "fewer than 30" days (from `assumptions.min_sample_days`). The published `insufficient_data` definition is shown, and the edge-case test asserts both. |
| 7 | NIT | The loading and error states had no footer, so no copyright line. | **Fixed.** The footer, with its links and copyright, appears in every state, including the error-boundary fallback. The data part (period, build date, attributions) appears only once data has loaded. The error message no longer repeats the footer's links. The loading and error visual references were regenerated and reviewed. |

**After the fixes:** 109 unit and component tests pass. 24 browser tests pass in the pinned image. 15 e2e tests pass against the `/travel-check/` build. JS is 85.6 KB gzip.

## Round 3 (main...a8b704c)

**Verdict:** APPROVE. 0 blocking, 2 should-fix, 5 nits.

**Automated checks, all passing:** `gen`, `format:check`, `lint`, `typecheck`, 109 unit and component tests, `build`, `size` (JS 85.63 KB gzip), 24 browser tests in the pinned image, and the pipeline's `schemas --check`. CI `web-lighthouse` passed on a8b704c.

### Findings and responses

| # | Severity | Finding | Response |
|---|---|---|---|
| 1 | SHOULD-FIX | The first card always had the accent border, which visually ranked it even when the page said "similar" or "not compared". | **Fixed.** The emphasis is a `card--higher` class, set only with the "Worked more often" badge. Three new e2e cases check the computed borders: 2 px and 1 px for "more", and 1 px and 1 px for the "similar" and insufficient-data cases. |
| 2 | SHOULD-FIX | A rate with status `ok` but fewer paired days than the minimum sample would have been shown and ranked. | **Fixed.** `buildLandingView` rejects status `ok` below `assumptions.min_sample_days`, as invalid data (unit test). |
| 3 | NIT | The summary named only the inbound airline for two-airline itineraries. | **Fixed.** One `itineraryName` function names both, in the card and the summary (component test). |
| 4 | NIT | The web rate check was exact, while the pipeline allows 1e-6. | **Fixed.** The same 1e-6 tolerance (unit tests for inside and outside it). |
| 5 | NIT | The touch-target test accepted a 24 px width. | **Fixed.** Standalone controls must be at least 44 px in both dimensions. |
| 6 | NIT | A negative arrival-day offset was computed but not shown. | **Fixed.** "−1 day" is shown. A unit case covers an arrival on the previous local day. |
| 7 | NIT | No tests for "fonts fail to load" and "prefers reduced motion". | **Fixed for fonts:** an e2e case aborts the font requests and checks the heading and a rate are visible. **Reduced motion is answered:** the page has no motion yet, and the CSS rule disables any future transitions. Playwright runs with `reducedMotion: "reduce"`, so the visual references are taken that way. A test belongs with the first animation (`explorer-core`). |

**After the fixes:** 112 unit and component tests pass. 28 browser tests pass in the pinned image (e2e 19, visual 4, a11y 3, keyboard 2). 19 e2e tests pass against the `/travel-check/` build. The visual references are unchanged. With an APPROVE verdict and every finding fixed or answered, the review loop ends. The owner decides on the merge (constitution, Development Workflow).
