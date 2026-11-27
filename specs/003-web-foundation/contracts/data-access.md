# Contract: Data-access module

`web/src/data/` is the only code that loads showcase data (FR-011). Screens use it through React hooks. The module is the swap point for a future API (FR-013).

## Interface

```ts
interface DataSource {
  getIndex(): Promise<Result<ShowcaseIndex>>;
  getLanding(): Promise<Result<RouteFile>>;
  getRoute(routeId: string): Promise<Result<RouteFile>>;
  getManifest(): Promise<Result<ShowcaseManifest>>;
}
```

The types `ShowcaseIndex`, `RouteFile` and `ShowcaseManifest` are imported from the generated `shared/types/showcase.ts` (`@contract`). `Result` and `DataError` are defined in [data-model.md](../data-model.md).

## Guarantees

1. **Validated or rejected.** A value returned with `ok: true` passed the compiled validator for its contract type. Anything else returns `ok: false` with `kind: "invalid"`. No partial data is ever returned.
2. **Failures are values, not exceptions.**
   - Network failures and HTTP errors return `kind: "network"`; a 404 returns `"not_found"`.
   - Hooks map any `ok: false` to the page's error state.
3. **Only known files.** `getRoute(routeId)` fetches only a route listed in the index's `routes[]`, at its `file` path; any other id returns `not_found` without fetching.
4. **Each file fetched once per page load.** Results are cached in memory; nothing is stored in the browser.
5. **No network in tests.** `memorySource(files)` takes a map from file path to parsed JSON, validates it the same way, and behaves the same for missing and malformed files.

## Implementations

| Name | Used by | Reads |
|---|---|---|
| `staticSource(baseUrl)` | the production app | `${baseUrl}data/showcase/{index,landing,manifest}.json` and `routes/*.json` |
| `memorySource(files)` | unit, component and malformed-data tests | in-memory fixtures, including the committed files loaded from disk in Node |

## Cross-checks: `buildLandingView`

`buildLandingView(index, landing, manifest)` returns `Result<LandingView>`. It fails with `invalid` when:
- `landing.route_id` differs from `index.landing.route_id`;
- no comparison in `landing.comparisons` has `comparison_id == index.landing.comparison_id`;
- either `itinerary_a` or `itinerary_b` of that comparison is missing from `landing.itineraries`.

## Hooks

`useLandingView()` returns `{ state: "loading" } | { state: "ready", view } | { state: "error" }`. It takes its source from `DataSourceContext`, which is provided once in `main.tsx`.

## Enforcement

- An ESLint rule forbids `fetch`, `XMLHttpRequest` and imports of `site-data` outside `web/src/data/`.
- A unit test checks that the rule is configured.
