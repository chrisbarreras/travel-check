# Quickstart: Web Foundation

Validation scenarios that show the feature works end to end. The commands are in [contracts/checks.md](contracts/checks.md), the data rules in [data-model.md](data-model.md).

## Prerequisites

- Node 24, the version in `web/.nvmrc`.
- Docker, for the browser tests in the pinned image.
- The committed showcase data in `site-data/showcase/`. No pipeline run is needed.

```sh
cd web
npm ci
npm run gen
```

## Scenarios

| # | Scenario | Command | Expected |
|---|---|---|---|
| 1 | Static checks pass (US2) | `npm run format:check && npm run lint && npm run typecheck` | exit 0 |
| 2 | Unit and component tests pass, offline (US2, US3) | `npm test` | all pass. Includes the display rules (rounding, "similar", "insufficient data", "+1 day") and the malformed-data cases |
| 3 | Build copies data unchanged (FR-016) | `npm run build` | `dist/data/showcase/` byte-identical to `site-data/showcase/` |
| 4 | Budgets hold (SC-002) | `npm run size` | JS ≤ 150 KB gzip; first-view data ≤ 150 KB gzip (about 9 KB today) |
| 5 | The page shows the landing figures exactly (US1, SC-003) | `npm run test:browser:docker` (project `e2e`) | LIT → LGA. Delta via ATL (most often DL3080 and DL524) worked on 92% of 298 days; United via ORD worked on 64% of 291 days; difference +28 points, 95% interval +22 to +35, over 242 days both flew; period Jul 2024 – Jun 2025. All values are asserted against the data files, not hard-coded |
| 6 | Phone layout (US1, SC-009) | same, at 320, 360, 768 and 1280 px | no horizontal scroll; touch targets ≥ 44 px; content reflows at 200% text zoom |
| 7 | Accessibility and keyboard (SC-004) | same (projects `a11y` and `keyboard`) | zero axe violations at WCAG 2.2 AA; every link and disclosure is reached in order, with visible focus |
| 8 | Visual references match (SC-006) | same (project `visual`) | screenshots match the committed references at 360 and 1280 px |
| 9 | Bad data gives an honest failure (US3) | `npm test` (malformed and failing source cases) and the `e2e` route-interception case | "This example could not be loaded"; no figures on the page |
| 10 | Lighthouse budgets (SC-001) | `npm run lighthouse` | median performance ≥ 0.90, accessibility 1.00, LCP ≤ 2.5 s, CLS ≤ 0.1 |
| 11 | Each breakage blocks a merge (SC-005) | a throwaway pull request per breakage: lint, type, unit, component, e2e, visual, a11y, keyboard, budget | the matching required check fails and the merge is blocked; the clean pull request passes. Results recorded in `validation.md` |
| 12 | Deployment and smoke check (SC-008) | merge to `main` | `web-deploy` succeeds and `npm run smoke -- https://chrisbarreras.github.io/travel-check/` passes within 10 minutes of the checks passing |
| 13 | CI time (SC-007) | any pull request | every web job finishes, and the slowest within 15 minutes |
| 14 | Reproducible screenshots (SC-006) | rerun the unchanged commit's `web-browser` job 3 times | all 3 pass |
