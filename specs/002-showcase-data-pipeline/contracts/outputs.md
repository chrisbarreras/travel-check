# Contract: Published Showcase Files

What the Phase 1 explorer reads. Shapes are defined once in `flight_pipeline.showcase` (Pydantic); `shared/schemas/showcase.schema.json` and `shared/types/showcase.ts` are generated from them and committed. Field-level detail: [data-model.md](../data-model.md).

## Files

| Path | Shape | Loaded |
|---|---|---|
| `site-data/showcase/index.json` | ShowcaseIndex | First, always |
| `site-data/showcase/landing.json` | RouteFile, restricted to the landing comparison, its two itineraries and any itinerary their insights refer to | First view, alone |
| `site-data/showcase/routes/{ORIGIN}-{DEST}.json` | RouteFile | When a route is opened |
| `site-data/showcase/manifest.json` | ShowcaseManifest | Not by the explorer; for `verify` and provenance |
| `shared/schemas/showcase.schema.json` | JSON Schema of every published shape | Build time |
| `shared/types/showcase.ts` | Generated TypeScript types | Build time |
| `shared/test-cases/slack-feasibility.json` | Shared test cases (research R7) | Tests in both languages |

## Rules

- **Stable bytes:** sorted keys, no insignificant whitespace, UTF-8, LF endings, floats rounded to 6 decimals; identical inputs give identical bytes (FR-025).
- **Validation:** every file is validated against its model when written, and the run stops on failure (FR-011).
- **Size:** the gzip-compressed total of `index.json`, `landing.json` and `routes/*.json` is at most `[showcase] size_budget_kb` (default 2048), and `index.json` plus `landing.json` together at most `[showcase] landing_budget_kb` (default 150, the load-time proxy for SC-007 until the explorer's Lighthouse checks exist); the run fails above either, reporting each file's size (FR-015).
- **Attribution:** `index.json` carries the required data attributions, which the explorer displays.
- **Honest values:** every rate is a `Rate` with status, sample and period; `insufficient_data` carries no rate (FR-013). Field names and texts use historical wording; no field is named or described as a probability or chance (FR-014).
- **Explicit absence:** empty `faster_alternatives`, `connecting_options` without a `better` entry, and an empty `changes` list all mean "none applies"; the explorer shows that, not an empty space (SC-005).
- **Coverage:** `index.json` carries `coverage` (FR-015a).
- **Route files:** each route file holds every itinerary in its showcase comparisons (curation keeps them within the maximum), then the route's other itineraries by sold passengers, up to `[showcase] itineraries_per_route_max`. Faster alternatives and connecting options may name itineraries of the route that are not in the file; each entry carries the figures shown.
- **Versioning:** `schema_version` follows semantic versioning; a breaking shape change bumps the major version.
