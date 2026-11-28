// How screens reach the data: one source, provided once in main.tsx (contracts/data-access.md,
// Hooks). Components never load data themselves.
import type { ShowcaseIndex } from "@contract";
import { createContext, use, useEffect, useState, type ReactNode } from "react";
import { buildLandingView, isTimestamp } from "./landing";
import { buildRouteView } from "./route";
import type { DataError, DataSource, LandingView, Result, RouteView } from "./types";

const DataSourceContext = createContext<DataSource | null>(null);

export function DataSourceProvider({
  source,
  children,
}: {
  source: DataSource;
  children: ReactNode;
}) {
  return <DataSourceContext value={source}>{children}</DataSourceContext>;
}

export type Loaded<T> = { state: "loading" } | { state: "ready"; view: T } | { state: "error" };

function useSource(): DataSource {
  const source = use(DataSourceContext);
  if (!source) throw new Error("data hooks need a DataSourceProvider");
  return source;
}

function report(error: DataError): Loaded<never> {
  console.error("Travel Check: showcase data could not be loaded", error);
  return { state: "error" };
}

/** Runs `load` for the current key; ignores answers for a key that is no longer current. */
function useLoaded<T>(key: string, load: () => Promise<Result<T>>): Loaded<T> {
  const [state, setState] = useState<{ key: string; loaded: Loaded<T> }>({
    key,
    loaded: { state: "loading" },
  });
  useEffect(() => {
    let current = true;
    void load().then((result) => {
      if (current) {
        setState({
          key,
          loaded: result.ok ? { state: "ready", view: result.value } : report(result.error),
        });
      }
    });
    return () => {
      current = false;
    };
    // `load` is recreated on each render; the key identifies what it loads.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return state.key === key ? state.loaded : { state: "loading" };
}

export type LandingState = Loaded<LandingView>;

export function useLandingView(): LandingState {
  const source = useSource();
  return useLoaded("landing", async () => {
    const [index, landing, manifest] = await Promise.all([
      source.getIndex(),
      source.getLanding(),
      source.getManifest(),
    ]);
    if (!index.ok) return index;
    if (!landing.ok) return landing;
    if (!manifest.ok) return manifest;
    return buildLandingView(index.value, landing.value, manifest.value);
  });
}

export interface ShowcaseView {
  index: ShowcaseIndex;
  builtAt: string;
}

/** The index and the build date, for the route picker and footer. */
export function useShowcase(): Loaded<ShowcaseView> {
  const source = useSource();
  return useLoaded("showcase", async (): Promise<Result<ShowcaseView>> => {
    const [index, manifest] = await Promise.all([source.getIndex(), source.getManifest()]);
    if (!index.ok) return index;
    if (!manifest.ok) return manifest;
    const builtAt = manifest.value.run.run_at;
    if (typeof builtAt !== "string" || !isTimestamp(builtAt)) {
      return {
        ok: false,
        error: { kind: "invalid", file: "manifest.json", detail: "run.run_at is not a timestamp" },
      };
    }
    return { ok: true, value: { index: index.value, builtAt } };
  });
}

/** One route's itineraries, loaded the first time the route is shown (FR-011). */
export function useRouteView(routeId: string): Loaded<RouteView> {
  const source = useSource();
  return useLoaded(`route:${routeId}`, async () => {
    const [index, route] = await Promise.all([source.getIndex(), source.getRoute(routeId)]);
    if (!index.ok) return index;
    if (!route.ok) return route;
    return buildRouteView(index.value, route.value, routeId);
  });
}
