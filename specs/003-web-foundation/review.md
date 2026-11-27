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
