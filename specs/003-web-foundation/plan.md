# Implementation Plan: Web Foundation

**Branch**: `003-web-foundation` | **Date**: 2026-11-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-web-foundation/spec.md`

**Approval**: spec and plan approved by the owner on 2026-11-27 (constitution, Development Workflow). The repository was published as `chrisbarreras/travel-check`, so the repository-visibility decision above is settled.

## Summary

Build the Phase 1 web application in `web/`: React, TypeScript and Vite. It is a placeholder page showing the landing comparison from the committed showcase data, with its rates, samples, interval, definitions and attributions. It follows `docs/design.md` and works from 320 px up.

**Data access:** all data comes through one `DataSource` module. It fetches the showcase files, which the build copies unchanged. It validates them with standalone validators compiled at build time from the generated JSON Schema, so the Pydantic models stay the only data contract.

**Checks:** around the page sits the full check suite:
- Prettier, ESLint and `tsc`;
- Vitest with Testing Library;
- Playwright e2e, visual, axe and keyboard projects, all run in a pinned Playwright container;
- Lighthouse CI, size-limit and a data-size budget.

**CI and hosting:** a new GitHub Actions workflow runs the suite on every push and pull request. A ruleset on `main` blocks merges on failure. The site deploys to GitHub Pages after merge, with a smoke check of the live URL. Hosting is recorded in ADR-0015 (research R1, R2).

**Owner decision before implementation:** GitHub Pages and the merge-blocking ruleset are free only on a **public** repository; the repository is private today. Recommendation: make it public. It is a portfolio project, no secrets or raw data are committed, and both features then cost nothing. If it stays private:
- hosting falls back to Cloudflare Pages, with an API token secret;
- FR-024 (merge blocking) needs a paid GitHub plan.

## Technical Context

**Language/Version**: TypeScript (strict), on Node 24 LTS (`web/.nvmrc`). The pipeline stays Python 3.13, unchanged.

**Primary Dependencies**: React 19, Vite 8, `@vitejs/plugin-react`; Ajv (build-time only, standalone validators); `@fontsource-variable/inter` and `@fontsource-variable/space-grotesk`. Exact versions are pinned, each released at least two weeks before installation.

**Storage**: none. The page reads static JSON copied from `site-data/showcase/`. Nothing is stored in the browser.

**Testing**: Vitest, jsdom and Testing Library (unit, component); Playwright with Chromium (e2e, visual, keyboard) and `@axe-core/playwright` (accessibility), in `mcr.microsoft.com/playwright:v1.65.0-noble` pinned by digest; `@lhci/cli` (performance); size-limit (bundle).

**Target Platform**: modern evergreen browsers on phones and desktops, served as a static site from GitHub Pages at `/travel-check/`.

**Project Type**: static web application (frontend only). It reads the pipeline's committed output.

**Performance Goals**:
- Landing figures visible within 2.5 s LCP, on Lighthouse's mobile profile;
- Lighthouse performance at least 0.90, accessibility 1.00.

**Constraints**:
- JS at most 150 KB gzip; first-view data at most 150 KB gzip;
- no network in tests;
- no third-party requests from the page;
- the CI suite under 15 minutes.

**Scale/Scope**: one page with three states (loading, ready, error); three data files on first view; 12 route files loadable but unused.

## Constitution Check

*GATE: checked before research, and again after the design.*

| Principle | Status | How |
|---|---|---|
| I. Statistical honesty | Pass | Every figure has its definition (verbatim from the index), its sample (`paired_days`, `shared_days`) and the period. "Insufficient data" is shown for that status, never a percentage. Precision is whole percent and whole points. The wording is historical. The "similar" rule uses the exact interval (data-model.md) |
| II. Automated verification | Pass | Display rules are pure functions written test-first. Every component ships with its tests. The checks are unit, component, e2e, visual in Docker, axe plus scripted keyboard tests, and Lighthouse with size budgets. Reference images change only through a reviewed update. Tests make no network calls. Map rules are not applicable: there is no map in this feature. No calculation is shared with the API yet: the page only formats published values |
| III. Thin, deployable slices | Pass | The spec lists out of scope. The feature ends deployed, and the README and `docs/architecture.md` are updated (FR-027) |
| IV. One data contract | Pass | Types come only from the generated `shared/types/showcase.ts`. Validators are compiled from the generated schema (R3), with no hand-written shapes. The page does no time-zone arithmetic: it formats the schedule's local minutes |
| V. Accessible and clear | Pass | Text and position, not color alone. Keyboard and screen-reader labels. 320 px up and 200% zoom. Freshness shown as the period and build date. Budgets set (SC-001, SC-002) |
| VI. Simplicity, replaceable providers | Pass | The `DataSource` interface is the provider boundary. No tool from ADR-0002's avoid list. One build-time code-generation step (R3), justified below |
| Technology follows the ADRs | Pass, with two new ADRs | GitHub Pages replaces ADR-0002's "Cloudflare Pages or Vercel" for the frontend: ADR-0015 records it and supersedes that row (R1). Plain CSS with design tokens replaces shadcn/ui and Tailwind, and the data-access module replaces TanStack Query (R10): ADR-0016 records both and supersedes those rows. It was added after review round 2 found the gap |
| Licences and attributions | Pass | BTS and airportsdata attributions shown verbatim from the index. The font licences ship with the packages, and the footer notes them |
| Workflow gates | Pass | Own branch. Owner approves spec and plan before implementation. Independent review rounds until APPROVE, saved in `review.md` |

**Post-design re-check:** no new violations. The one added mechanism is the build-time validator generation, recorded under Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/003-web-foundation/
├── plan.md            # this file
├── research.md        # R1–R13 decisions
├── data-model.md      # fields read, display rules, browser-only types
├── quickstart.md      # validation scenarios
├── contracts/
│   ├── data-access.md # DataSource interface and guarantees
│   └── checks.md      # commands, CI jobs, required checks
├── checklists/requirements.md
└── tasks.md           # /speckit-tasks
```

### Source Code (repository root)

```text
web/
├── package.json, package-lock.json, .nvmrc
├── vite.config.ts          # base path, copy of site-data/showcase, @contract alias
├── tsconfig.json, eslint.config.js, .prettierrc.json
├── playwright.config.ts    # projects: e2e, visual, a11y, keyboard, smoke
├── lighthouserc.json, .size-limit.json
├── scripts/
│   ├── gen-validators.mjs  # Ajv standalone from ../shared/schemas/showcase.schema.json
│   ├── check-data-size.mjs
│   └── check-data-copy.mjs # dist/data/showcase byte-identical to site-data/showcase
├── index.html
├── src/
│   ├── main.tsx            # creates staticSource and provides DataSourceContext
│   ├── App.tsx             # loading / ready / error
│   ├── data/               # DataSource, staticSource, memorySource, validate, buildLandingView, hooks
│   │   └── generated/      # validators (git-ignored, rebuilt by npm run gen)
│   ├── format/             # rates, points, intervals, times, durations, period, airline names
│   ├── components/         # LandingComparison, ItineraryCard, Difference, Definition, Footer, Skeleton, LoadError
│   └── styles/             # tokens.css (design.md tokens), global.css
└── tests/
    ├── unit/  component/   # Vitest
    ├── e2e/  a11y/  keyboard/  smoke/
    ├── visual/             # with __screenshots__/ references
    └── fixtures/           # malformed and edge-case data

.github/workflows/web.yml   # checks, browser, lighthouse, deploy
docs/architecture.md        # new: pipeline → showcase files → data-access → page
docs/adr/0015-static-hosting-github-pages.md
README.md                   # live link, run, test, build
```

**Structure Decision:** one new top-level `web/` project next to `pipeline/`. The two meet only at the committed `shared/` contract and the `site-data/showcase/` files. Nothing in `pipeline/` changes.

## Delivery Order

The order matches the spec's stories, so each step can be checked on its own:
1. **Setup:** scaffold `web/`, the toolchain and validator generation.
2. **Foundation:** the data-access module and display rules, test-first (the base of US3 and US1).
3. **US1:** the page and its components, with unit, component and e2e tests.
4. **US2:** the browser test projects in Docker, Lighthouse and budgets, the CI workflow, deployment, the ruleset and the breakage tests.
5. **US3:** the error and loading states, plus the malformed-data and failing-source tests.
6. **Polish:** README, `docs/architecture.md`, ADR-0015, `validation.md`, then the independent review.

## Complexity Tracking

| Addition | Why needed | Simpler alternative rejected because |
|---|---|---|
| Build-time generation of standalone validators (`npm run gen`) | FR-012 requires checking loaded data against the contract. Principle IV forbids a second, hand-written definition | Zod or Valibot schemas would duplicate the contract by hand. Ajv at run time would add about 35 KB of compiler to the page |
| A pinned Playwright container for browser tests | FR-019 and SC-006 require identical screenshots on any machine. Fonts and rendering differ across operating systems | Running Playwright directly on each machine gives pixel differences between Windows, macOS and Linux |
