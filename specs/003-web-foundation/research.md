# Research: Web Foundation

Decisions for [spec.md](spec.md), each with its rationale and the alternatives considered. Versions are pinned exactly, each released at least two weeks before installation. The lockfile records the full tree.

## R1. Hosting

**Decision:** GitHub Pages, deployed from GitHub Actions with the official `actions/upload-pages-artifact` and `actions/deploy-pages` actions. It is a project site at `https://chrisbarreras.github.io/travel-check/`. This needs the repository to be public, or a paid GitHub plan; see R2. Record the choice in ADR-0015, which supersedes ADR-0002's hosting row for the frontend. The Phase 2 API host is still chosen in Phase 2.

**Rationale:**
- Free, with no second account or long-lived deploy token: the deploy job authenticates with the workflow's own short-lived OIDC token.
- A failed deployment leaves the previous site live (FR-025).
- Serves gzip.
- Simplest option that meets the spec (constitution, Principle VI).

**Alternatives:**
- **Cloudflare Pages** (ADR-0002's first choice): better caching control (`_headers`), Brotli, and it works with a private repository. But it needs a Cloudflare account and an API token stored as a repository secret. It is the fallback if the repository stays private.
- **Vercel:** same account and token cost. Its free tier limits commercial use, and Phase 5 keeps a commercial path open.

**Consequence:** GitHub Pages sets `Cache-Control: max-age=600` on everything, and it can't be changed. That's acceptable for a placeholder: Lighthouse runs against a local server (R7), and first-visit performance is unaffected. Revisit when the map arrives in `explorer-core`.

## R2. Merge blocking

**Decision:** a repository ruleset on `main`:
- require a pull request;
- require these status checks to pass: `pipeline / checks` plus the web workflow's `checks`, `browser` and `lighthouse`;
- block force pushes and deletion.

It is created with `gh api` once the owner authorizes it. Every required job runs on every pull request, with no path filters, because a filtered-out required check stays pending and blocks merging.

**Rationale:** rulesets and branch protection are free on public repositories, but not on private repositories on the free plan. FR-024 therefore needs the repository to be public, or a paid plan. This is the owner decision named in the plan.

**Alternatives:**
- **A check that "fails" without a ruleset:** that doesn't block anything.
- **A paid plan:** possible, but not needed for a portfolio project meant to be public.

## R3. Runtime validation of loaded data

**Decision:** compile standalone validator functions at build time from the generated `shared/schemas/showcase.schema.json`, using Ajv's 2020-12 build and its standalone code output: one each for `ShowcaseIndex`, `RouteFile` (also used for `landing.json`) and `ShowcaseManifest`. The generated module goes in `web/src/data/generated/`, which git ignores, and is rebuilt before every type check, test and build. A small hand-written function then checks the cross-references the schema can't express: the landing comparison exists in the landing file, and both of its itineraries are present.

**Rationale:**
- The schema generated from the Pydantic models stays the only definition of the data's shape (constitution, Principle IV; ADR-0007).
- Standalone code avoids shipping the Ajv compiler to the browser: the validators are a few kilobytes, not about 35 KB.

**Alternatives:**
- **Zod or Valibot:** these would mean writing the data shape a second time by hand, which Principle IV forbids.
- **No runtime validation, trusting the types:** a type is a compile-time promise. It doesn't catch a corrupt or mismatched file at run time, so FR-012 couldn't be met.
- **Ajv at run time:** adds the compiler to the bundle.

## R4. How data reaches the page

**Decision:** the build copies `site-data/showcase/` unchanged into the output at `data/showcase/` (FR-016). The data-access module fetches files relative to the site's base path. The first view loads only `index.json`, `landing.json` and `manifest.json`, about 9 KB compressed. The base path is `/travel-check/` in production and `/` locally, set at build time.

**Rationale:**
- Keeps the data out of the script bundle (SC-002).
- Byte-identical files, so `verify`'s checksums still describe what the site serves.
- Fetching is what a future API would replace (FR-013).

**Alternatives:**
- **Importing the JSON into the bundle:** the data would count against the script budget, and the data source couldn't be swapped later.
- **A symlink to `site-data`:** symlinks are fragile on Windows and in the Pages artifact.

## R5. Unit and component tests

**Decision:** Vitest with jsdom, plus Testing Library (`react`, `user-event`, `jest-dom`). Pure formatting and display rules sit in `web/src/format/` and are tested exhaustively, including property-style cases such as rounding at the halves and arrival on the next day. Components are tested against an in-memory data source (R10).

**Rationale:** Vitest is the stack choice in ADR-0002, shares Vite's configuration, and is fast.

**Alternatives:** Jest (separate transform setup) and the browser mode of Vitest (slower; Playwright covers real browsers).

## R6. End-to-end, visual, accessibility and keyboard tests

**Decision:** Playwright with Chromium, in four projects:
1. **e2e:** at 320, 360, 768 and 1280 px. It compares page figures with the data files, read in the test from `site-data/showcase/` (FR-018).
2. **visual:** at 360 and 1280 px, with `toHaveScreenshot`, animations disabled and the self-hosted fonts loaded.
3. **a11y:** `@axe-core/playwright` with the `wcag2a`, `wcag2aa`, `wcag21aa` and `wcag22aa` tags, at both sizes.
4. **keyboard:** a scripted Tab and Shift+Tab walk asserting order, visible focus and activation.

All four run against the production build served by `vite preview`, with no network. Requests outside the local server are blocked in the test fixture (FR-022).

**Reproducible screenshots:** all Playwright projects run inside the official image `mcr.microsoft.com/playwright:v1.65.0-noble`, pinned by digest. That's true both in CI (as the job's container) and locally (`npm run test:browser:docker`). Reference images are committed under `web/tests/visual/__screenshots__/`. They change only through `npm run test:visual:update`, which runs in the same container, and the diff is reviewed in the pull request (FR-019). CI never updates them.

**Alternatives:**
- **WebKit and Firefox as well:** triples the run time for a placeholder. Chromium with mobile viewport and touch emulation covers the phone layout. Add other browsers when the map arrives.
- **A hosted visual service** (Percy, Chromatic): needs a network and an account.

## R7. Performance budgets

**Decision:**
- **Lighthouse CI** (`@lhci/cli`) against the production build on a local static server. It uses the mobile preset: simulated throttling, Moto G Power class. It does 3 runs and asserts on the median:
  - performance at least 0.90;
  - accessibility 1.00;
  - largest contentful paint at most 2,500 ms;
  - cumulative layout shift at most 0.1.

  Reports are kept as CI artifacts, not uploaded anywhere.
- **size-limit** for the script budget: all JS at most 150 KB gzip.
- **A data-size check script** for the data the first view loads: at most 150 KB gzip (SC-002).

**Rationale:** these are the standard tools named by the constitution. A local server keeps the check deterministic and offline. Simulated throttling is far more stable than device emulation.

**Alternatives:** Lighthouse against the live site (network-dependent and runs after merge, too late to block) and WebPageTest (external service).

## R8. Fonts

**Decision:** self-host the variable fonts `@fontsource-variable/inter` and `@fontsource-variable/space-grotesk`, Latin subset only, with `font-display: swap`. Fall back to the system UI stack.

**Rationale:**
- No third-party requests, which keeps the tests offline.
- No visitor IPs sent to Google.
- One file per family, which keeps loading small. Both fonts are under the SIL Open Font License; the licence files ship with the packages.

**Alternative:** Google Fonts CDN (a network dependency in tests, a third-party request in production).

## R9. Lint, format and types

**Decision:**
- **ESLint** flat configuration with `typescript-eslint` (type-aware strict rules), `eslint-plugin-react-hooks` and `eslint-plugin-jsx-a11y`.
- **Prettier 3.10.1**, the same version the pipeline uses for generated types.
- **TypeScript** in strict mode with `noUncheckedIndexedAccess`; `tsc --noEmit` in CI.
- **Generated types:** imported from `shared/types/showcase.ts` through a path alias (`@contract`), never copied.

**Rationale:** catches unsafe data access at compile time, and the accessibility lint catches problems before axe does.

## R10. Data-access module

**Decision:** a `DataSource` interface (`getIndex()`, `getLanding()`, `getRoute(routeId)`, `getManifest()`), all asynchronous and all returning validated data or a typed error. It has two implementations:
- `staticSource(baseUrl)`, which fetches the copied files;
- `memorySource(files)`, for tests.

The app receives its source through a React context created once in `main.tsx`. Components read through hooks (`useLanding()` and similar) and never call `fetch`. ESLint's `no-restricted-globals` and `no-restricted-imports` rules enforce that outside `web/src/data/` (FR-011).

**Rationale:**
- One swap point for the Phase 2 API (FR-013; constitution, Principle VI on provider interfaces).
- Tests can substitute data without any network (FR-022).

**Alternatives:** a data-fetching library such as TanStack Query (unnecessary for three static files; revisit in Phase 2) and global fetch calls in components (no swap point).

## R11. Display rules

**Decision:**
- **Rounding:** rates to whole percent and differences to whole points, rounding halves away from zero. This is the pipeline's rule (feature 002, `rate_of_days`) and keeps negative differences symmetrical.
- **Wording when the interval includes zero:** "similar" vs "worked more often", decided on the exact interval from the data, never on rounded values.
- **Interval display:** "95% interval +22 to +35 points".
- **Times:** each shown in its airport's local time, from the schedule's local minutes. The format is "12:38 pm", with "+1 day" when the minutes pass midnight, and the label "local time".
- **Period:** "Jul 2024 – Jun 2025", from the data's period.
- **Insufficient data:** a rate whose status is `insufficient_data` shows "insufficient data" with its day count, never a percentage.

**Rationale:** the constitution, Principle I, and the design document's precision and wording rules. These are pure functions with exhaustive unit tests.

## R12. Continuous integration

**Decision:** a new workflow, `.github/workflows/web.yml`, alongside the existing `pipeline.yml`, which stays unchanged. It runs on every push and pull request.

| Job | Contents | Needs |
|---|---|---|
| `checks` | `npm ci`; generate validators; Prettier, ESLint, `tsc`; Vitest; build; size-limit; data-size check | |
| `browser` | In the pinned Playwright container: build, then the e2e, visual, a11y and keyboard projects; uploads the report and diffs on failure | |
| `lighthouse` | Build, then Lighthouse CI with the assertions in R7 | |
| `deploy` | Only on push to `main`: build, upload the Pages artifact, deploy, then a smoke test of the live URL with Playwright | `checks`, `browser`, `lighthouse` |

Node 24 (LTS), pinned in `.nvmrc` and `engines`. npm with a committed `package-lock.json`, so `npm ci` is reproducible. Actions are pinned to major versions, as in `pipeline.yml`.

**Rationale:**
- Parallel jobs keep the run under 15 minutes (SC-007).
- The smoke test is the only step that uses the network, and it is outside the test suite (spec, Clarifications).

## R13. Owner steps

These need the repository owner and can't be done by an agent alone:
1. Decide whether to make the repository public (R1, R2).
2. Enable Pages with "GitHub Actions" as the source. This can be done with `gh api` once authorized.
3. Create the ruleset (R2). This can be done with `gh api` once authorized.
