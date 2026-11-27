# Contract: Commands and CI checks

All commands run from `web/`. Each exits non-zero on failure. CI runs exactly these commands (FR-026).

## Commands

| Command | What it does | Fails when |
|---|---|---|
| `npm run gen` | Compiles the standalone validators from `../shared/schemas/showcase.schema.json` into `src/data/generated/` | The schema is missing or invalid |
| `npm run format:check` | Prettier check | A file is not formatted |
| `npm run lint` | ESLint | Any error. Warnings count as errors |
| `npm run typecheck` | `tsc --noEmit` (strict) | Any type error |
| `npm test` | Vitest: unit and component tests | Any failing test |
| `npm run build` | Production build to `dist/`, including the showcase data copied unchanged | A build error, or a copied file whose checksum differs from the source |
| `npm run size` | size-limit on `dist/assets/*.js`; the data-size check on the files the first view loads | JS above 150 KB gzip, or first-view data above 150 KB gzip |
| `npm run test:browser` | Playwright projects `e2e`, `visual`, `a11y` and `keyboard` against `vite preview` of `dist/` | Any failure. Refuses to run the `visual` project outside the pinned container |
| `npm run test:browser:docker` | The same, inside the pinned Playwright image, for local use | as above |
| `npm run test:visual:update` | Rewrites the reference images, inside the pinned image only | never in CI |
| `npm run lighthouse` | Lighthouse CI: 3 runs, mobile preset, against `dist/` on a local server | performance below 0.90, accessibility below 1.00, LCP above 2,500 ms, or CLS above 0.1 (median) |
| `npm run smoke -- <url>` | Playwright smoke check of a deployed URL. It uses the network and is not part of the test suite | The page fails to load, or the landing figures differ from the data in `dist/` |

## CI (`.github/workflows/web.yml`)

The workflow runs on every push and every pull request, with no path filters.

| Job (status-check name) | Runs | Required for merge |
|---|---|---|
| `web / checks` | `npm ci`, `gen`, `format:check`, `lint`, `typecheck`, `test`, `build`, `size` | yes |
| `web / browser` | `test:browser`, in the pinned Playwright container. Reports and diffs are uploaded on failure | yes |
| `web / lighthouse` | `build`, `lighthouse`. Reports are uploaded as artifacts | yes |
| `web / deploy` | Push to `main` only, after the three jobs above: build with the production base path, upload the Pages artifact, deploy, then `smoke` on the deployed URL | no; it runs after merge |
| `pipeline / checks` | existing, unchanged | yes |

## Reference images

- Committed in `web/tests/visual/__screenshots__/`, one per page state and width.
- Changed only by `npm run test:visual:update` in the pinned image, and reviewed as image diffs in the pull request (constitution, Principle II).
- When showcase data changes the numbers on screen, the images are updated in the same pull request.
