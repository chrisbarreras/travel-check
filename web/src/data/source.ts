// The two DataSource implementations (contracts/data-access.md). Both share one loader, so a
// test source and the production source validate and fail in exactly the same way.
import type { RouteFile, ShowcaseIndex, ShowcaseManifest } from "@contract";
import type { DataSource, Result } from "./types";
import { checkIndex, checkManifest, checkRouteFile } from "./validate";

/** Reads one file's parsed JSON, or reports why it could not. */
type Load = (file: string) => Promise<Result<unknown>>;

function createSource(load: Load): DataSource {
  // Each file is loaded once per page load (Guarantee 4).
  const cache = new Map<string, Promise<Result<unknown>>>();
  const once = (file: string): Promise<Result<unknown>> => {
    let pending = cache.get(file);
    if (!pending) {
      pending = load(file);
      cache.set(file, pending);
    }
    return pending;
  };

  async function get<T>(
    file: string,
    check: (file: string, data: unknown) => Result<T>,
  ): Promise<Result<T>> {
    const loaded = await once(file);
    return loaded.ok ? check(file, loaded.value) : loaded;
  }

  const getIndex = (): Promise<Result<ShowcaseIndex>> => get("index.json", checkIndex);

  return {
    getIndex,
    getLanding: () => get("landing.json", checkRouteFile),
    getManifest: (): Promise<Result<ShowcaseManifest>> => get("manifest.json", checkManifest),
    async getRoute(routeId: string): Promise<Result<RouteFile>> {
      // Only routes listed in the index are fetched, at their listed path (Guarantee 3).
      const index = await getIndex();
      if (!index.ok) return index;
      const route = index.value.routes.find((r) => r.route_id === routeId);
      if (!route) {
        return {
          ok: false,
          error: { kind: "not_found", file: routeId, detail: "not listed in index.json" },
        };
      }
      return get(route.file, checkRouteFile);
    },
  };
}

/** The production source: the showcase files copied into the build at data/showcase/. */
export function staticSource(
  baseUrl: string,
  fetchImpl: (url: string) => Promise<Response> = (url) => fetch(url),
): DataSource {
  const root = `${baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`}data/showcase/`;
  return createSource(async (file) => {
    let response: Response;
    try {
      response = await fetchImpl(`${root}${file}`);
    } catch (error) {
      return { ok: false, error: { kind: "network", file, detail: String(error) } };
    }
    if (response.status === 404) {
      return { ok: false, error: { kind: "not_found", file, detail: "HTTP 404" } };
    }
    if (!response.ok) {
      return {
        ok: false,
        error: { kind: "network", file, detail: `HTTP ${String(response.status)}` },
      };
    }
    try {
      return { ok: true, value: (await response.json()) as unknown };
    } catch (error) {
      return { ok: false, error: { kind: "invalid", file, detail: `not JSON: ${String(error)}` } };
    }
  });
}

/** A source over parsed files held in memory, keyed by path below data/showcase/ (tests). */
export function memorySource(files: Readonly<Record<string, unknown>>): DataSource {
  return createSource((file) =>
    Promise.resolve(
      file in files
        ? { ok: true, value: structuredClone(files[file]) }
        : { ok: false, error: { kind: "not_found", file, detail: "not in memory" } },
    ),
  );
}
